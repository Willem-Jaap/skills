#!/usr/bin/env bash
# Commit screenshots to the repo's orphan `pr-screenshots` branch under pr-<number>/,
# push it, and print one embeddable URL per image. The working tree, the index and
# the current branch are never touched. Run from inside the repo.
#
# Usage: upload-screenshots.sh <pr-number> <image>...
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "usage: $(basename "$0") <pr-number> <image>..." >&2
  exit 1
fi

pr="$1"
shift

case "$pr" in
  '' | *[!0-9]*)
    echo "pr number must be numeric: $pr" >&2
    exit 1
    ;;
esac

for file in "$@"; do
  if [ ! -f "$file" ]; then
    echo "not a file: $file" >&2
    exit 1
  fi
  case "$(basename "$file")" in
    *[!A-Za-z0-9._-]*)
      echo "use only letters, digits, dots, dashes and underscores in names: $file" >&2
      exit 1
      ;;
  esac
done

branch=pr-screenshots
url=$(git config --get remote.origin.url)
slug=$(printf '%s' "$url" | sed -E 's#/$##; s#\.git$##' | sed -nE 's#^.*github\.com[:/]([^/]+/[^/]+)$#\1#p')
if [ -z "$slug" ]; then
  slug=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
fi

scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
export GIT_INDEX_FILE="$scratch/index"

commit=""
for attempt in 1 2 3; do
  rm -f "$GIT_INDEX_FILE"
  parent=""

  set +e
  git ls-remote --exit-code --heads origin "$branch" >/dev/null
  status=$?
  set -e

  if [ "$status" -eq 0 ]; then
    git fetch -q origin "refs/heads/$branch"
    parent=$(git rev-parse FETCH_HEAD)
    git read-tree "$parent"
  elif [ "$status" -eq 2 ]; then
    readme=$(printf '# Pull request screenshots\n\nShown in pull request descriptions, one folder per pull request. This branch is never merged.\n' | git hash-object -w --stdin)
    git update-index --add --cacheinfo "100644,$readme,README.md"
  else
    echo "could not reach origin" >&2
    exit 1
  fi

  for file in "$@"; do
    blob=$(git hash-object -w "$file")
    git update-index --add --cacheinfo "100644,$blob,pr-$pr/$(basename "$file")"
  done

  tree=$(git write-tree)
  if [ -n "$parent" ] && [ "$tree" = "$(git rev-parse "$parent^{tree}")" ]; then
    commit="$parent"
    break
  fi

  commit=$(git commit-tree "$tree" ${parent:+-p "$parent"} -m "docs: add screenshots for pull request $pr")
  if git push -q origin "$commit:refs/heads/$branch"; then
    break
  fi

  if [ "$attempt" -eq 3 ]; then
    echo "push to $branch failed three times" >&2
    exit 1
  fi
done

for file in "$@"; do
  echo "https://github.com/$slug/blob/$commit/pr-$pr/$(basename "$file")?raw=true"
done
