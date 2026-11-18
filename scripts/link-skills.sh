#!/usr/bin/env bash
# Symlink every skill in this repo into ~/.claude/skills and ~/.agents/skills,
# so a `git pull` updates the installed skills. Rerun after adding or renaming one.
# A real directory with the same name is left alone unless you pass --force.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

for dest in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  mkdir -p "$dest"
  for src in "$REPO"/skills/*/; do
    src="${src%/}"
    [ -f "$src/SKILL.md" ] || continue
    target="$dest/$(basename "$src")"
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      if [ "$FORCE" = 0 ]; then
        echo "skip $target: a real directory. Check with \`diff -r $target $src\`, then rerun with --force."
        continue
      fi
      rm -rf "$target"
    fi
    ln -sfn "$src" "$target"
    echo "linked $target -> $src"
  done
done
