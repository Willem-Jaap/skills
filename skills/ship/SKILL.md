---
name: ship
description: Ship a Linear issue end to end in any repo. Starts from the latest default branch, implements, verifies, commits, pushes and opens a draft PR that says what it fixes, why and how, with screenshots for UI changes and a checkbox list of what was tested. Resumable, a rerun only does the missing steps. Use as /ship PIX-123 or /ship <linear issue url>.
argument-hint: "[PIX-123 | linear issue url] [--ready] [reviewer] [notes]"
disable-model-invocation: true
---

# Ship

Arguments: `$ARGUMENTS` (if that was not substituted, use the text after the skill name in the user's message).

- **Issue**: the first `[A-Z]+-[0-9]+` in the arguments, bare (`PIX-2481`) or inside a Linear URL (`https://linear.app/<workspace>/issue/PIX-2481/<slug>`). None given: take it from the current branch name (`pix-2481-...`). Still none: there is no issue yet.
- **`--ready`**: open the PR ready for review. Without it the PR is always a draft.
- **A GitHub handle**: request that reviewer. Never request the PR author, GitHub rejects it.
- **Anything else**: extra instructions for the implementation.

The flow is resumable. Detect what already exists first and only do the missing steps. Never create a second branch, commit, PR or screenshot set for the same work.

## 1. Read the repo and the issue

In parallel:

- **Repo conventions**: `AGENTS.md` and `CLAUDE.md` at the root (and any nearer to the code you will touch), plus the rule files they point to (`.claude/rules/`, `.cursor/rules/`). They decide commit format, scopes, checks and writing rules.
- **Repo overlay**: if the repo has `.claude/skills/ship/SKILL.md` and it is not this file, read it. It holds repo settings (Linear project, base branch notes, checks, how to log in for screenshots). Its settings win over the defaults here; the flow stays this one.
- **Base branch**: `git fetch origin --prune`, then `git symbolic-ref --short refs/remotes/origin/HEAD` minus the `origin/` prefix, falling back to `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`. Called `<base>` below, usually `master`. Always compare and branch against `origin/<base>`, never a local copy that may be stale.
- **Local state**: `git status --porcelain`, `git branch --show-current`, `git rev-list --count origin/<base>..HEAD`, `git worktree list`.
- **Issue**: Linear `get_issue` with relations, `list_comments`, and anything it links (documents, attachments, images that carry the spec). It gives `gitBranchName`, project, state, blockers.
- **Existing PR**: `gh pr list --head <gitBranchName> --state all --json number,url,state,isDraft`.

Stop and tell the user (ask with `AskUserQuestion` when you are in an interactive session) when:

- the issue's Linear project clearly belongs to a different repo than the one you are in. Name the right repo if you can tell.
- the issue is blocked by an issue that is not done.
- the description or comments leave a decision open that changes what you would build. Ask, do not pick for them.
- the issue is already Done or Canceled.

**No issue given and there are changes to ship**: create one with Linear `save_issue` in a single call: the team and project that belong to this repo (overlay first, otherwise match the repo name against `list_projects`, ask if unclear), assignee `me`, the best-fitting label (Bug, Improvement, Feature), a sensible priority, title and description from the diff plus the arguments. Use the `gitBranchName` it returns. **No issue and no changes**: ask what to ship.

## 2. Start from the latest base

The branch is always the issue's `gitBranchName`. Never invent a name, never commit to or push `<base>`, and never stash, reset or overwrite uncommitted work that is not this issue's.

Take the first case that matches:

1. **Already on `gitBranchName`**: stay. If it was never pushed and is behind `origin/<base>`, `git rebase origin/<base>`. If it was pushed, do not rewrite it; note in the report how far behind it is.
2. **The branch exists in another worktree** (`git worktree list`): work there. Claude Code: `EnterWorktree` with its `path` when it lives under `.claude/worktrees/`, otherwise use absolute paths.
3. **This checkout is free**: the tree is clean and `HEAD` has no commits that are not on `origin/<base>` (a base checkout or a fresh worktree). `git switch <gitBranchName>` when it exists on origin, otherwise `git switch -c <gitBranchName> origin/<base>`.
   - Same, but the uncommitted changes are this issue's work (started on the base branch): carry them over with `git stash push -u`, `git switch -c <gitBranchName> origin/<base>`, `git stash pop`.
4. **Anything else** (on another feature branch, or uncommitted work that belongs to something else): leave this checkout alone and work in a separate worktree started from `origin/<base>`.
   - **T3 Code** (a `t3_worktree_handoff` tool exists and `t3_worktree_status` says the thread has no worktree): call `t3_worktree_handoff` with `branch: <gitBranchName>`, `baseRef: <base>`, `startFromOrigin: true` and a `continuationPrompt` such as "Continue shipping PIX-2481: read ~/.agents/skills/ship/SKILL.md and follow it from step 3. Arguments: <original arguments>". It must be the last call of the turn.
   - **Claude Code otherwise**: `git worktree add .claude/worktrees/<issue-id> -b <gitBranchName> origin/<base>` (no `-b` if the branch already exists), then `EnterWorktree` with that `path`.
   - **Any other harness**: `git worktree add ../<repo>-<issue-id> ...` and work with absolute paths.
   - Tell the user where the worktree is.

A fresh worktree (made here, by T3, by `/threadship` or by a batch run) may have no dependencies and no untracked env files. Install what the checks need (`pnpm install --prefer-offline`, `composer install`, ...) and copy the untracked `.env` files the repo needs from the main checkout.

## 3. Implement

Skip this step when the branch already implements the whole issue. Compare its diff against the issue and finish whatever is missing.

- Read the relevant code first, then implement the whole issue plus the extra instructions, following the repo conventions and mirroring the closest sibling file.
- If the change alters existing UI, take the **before** screenshots now (see step 5), while the checkout still runs the base code.
- Add or update tests where the repo has a test suite for that area.
- Never put issue ids in code comments. No drive-by refactors; note follow-ups for the report instead.
- If the issue turns out much larger than it looked, or ambiguous, ask. In a subagent with nobody to ask, stop before pushing and report back. A skipped issue is fine, an invented requirement is not.

## 4. Verify

- Run the checks the repo defines for the paths you touched: format and lint, type check, static analysis, tests. Look in the `AGENTS.md` command table, `package.json` / `composer.json` scripts, and as a last resort `.github/workflows`. Fix what fails and rerun.
- Exercise the change for real where you can: load the page, call the endpoint, run the command, and confirm it does what the issue asks.
- Keep a log of every check: the command or action and its result. It becomes the Testing list in step 6. Anything you could not run (Docker down, needs production data or credentials) is recorded as not verified, with the reason.
- Read the full diff once (`git diff origin/<base>`) for leftover debug code, unrelated changes and secrets.

## 5. Screenshots (UI changes only)

A UI change is anything that changes what a person sees: components, pages, styles, copy, emails, templates. A change without visible effect gets no screenshots and no Screenshots heading.

**Capture**

- Run the app as the repo describes. Make sure the server you hit serves this checkout, since another worktree may hold the port: `lsof -a -p "$(lsof -nP -iTCP:<port> -sTCP:LISTEN -t | head -1)" -d cwd`.
- Use headless Chrome through `~/.agents/skills/ship/scripts/screenshot.mjs`: copy it to a scratch dir, `npm i playwright-core` there, run it with `node`. It uses the installed Google Chrome; on a machine without it, run `npx playwright-core install chromium` once and it falls back to that. The default is 1440x900 at 2x. Add a 390-wide shot when the change affects a responsive layout, and a dark shot when it affects colors in an app that has dark mode. Crop to the changed area with `--selector` when the page is large, and use `--wait` to get past skeletons. Copy and extend the script for logins or clicks. The overlay or the repo docs often say how to log in locally.
- Before and after pairs for changes to existing UI, after only for new UI.
- Look at every image before using it: it shows the change, it has no skeletons or error overlays, and it shows no real customer data or secrets.
- If you cannot capture (the app will not run here, login unavailable), add an unchecked Testing item saying so and why. Do not skip it silently.

**Upload** (needs the PR number, so after the PR exists): from inside the repo, run `~/.agents/skills/ship/scripts/upload-screenshots.sh <pr-number> <file>...` with kebab-case file names. It commits the images to the orphan `pr-screenshots` branch under `pr-<number>/` without touching the working tree, pushes it and prints one URL per file. Never commit screenshots to the feature branch. For a repo not on GitHub, say in the report that the screenshots still need attaching.

**Embed**, between markers so a rerun can replace the block:

```markdown
<!-- screenshots:start sha=<head commit the screenshots show> -->
## Screenshots

Before: <one line on what to notice>.
<img src="<url>" alt="<what the image shows>" width="800">

After: <one line on what changed>.
<img src="<url>" alt="<what the image shows>" width="800">
<!-- screenshots:end -->
```

Use `width="800"` for desktop shots and `width="300"` for phone-width ones. On a rerun, if the UI changed after the `sha` in the marker, retake the screenshots and replace the block.

## 6. Commit, push, PR

**Commit** only the files that belong to this work (`git add <paths>`, never `git add -A` next to unrelated changes). Follow the repo's commit convention; the default is Conventional Commits, `<type>(<scope>): <description>`, imperative, lowercase, no trailing period. One commit, or a few logical ones. Never add a `Co-Authored-By` trailer or any "Generated with" line, in commits or in PRs.

**Push** when there is something unpushed: `git push -u origin <gitBranchName>`. Never force-push a branch that has a PR unless the user asks.

**PR**. If one is open for the branch, do not open another: update its body to match the branch as it is now and keep anything a person added to it. Never undraft an existing PR unless the user asks. Otherwise create one, writing the body to a temp file first:

```bash
gh pr create --draft --base <base> --head <gitBranchName> --assignee @me --title "<title>" --body-file <file>
```

- Leave out `--draft` only with `--ready`. Add `--reviewer <handle>` only when the arguments or the overlay name one, then confirm it stuck with `gh pr view --json reviewRequests` (GitHub drops unknown handles without an error).
- The title follows the commit convention and describes the whole change, for example `fix(frontend): start dashboard sparklines at the site's first event`.
- With UI changes: upload the screenshots now (step 5), add the block, `gh pr edit <number> --body-file <file>`.
- In T3 Code: call `link_pull_request` with the PR URL right after creating it.

**Body**. Follow the repo's writing rules (for example a ban on em and en dashes) and write for a reviewer who has not read the issue:

```markdown
## What

<What this fixes or adds, from the user's side. For a bug: what went wrong and when.>

## Why

<Why it matters. For a bug, the root cause. Why this approach over the obvious alternative.>

## How

- <The changes by area: files, functions, data, migrations. Enough to know where to look.>
- <Decisions, trade-offs, what was deliberately left out.>

<screenshots block, UI changes only>

## Testing

- [x] `<command>`: <what it covers>, <result, e.g. 48 passed>
- [x] <Manual check>: <what you did and what you saw>
- [ ] <Not verified>: <what, why, and how a reviewer can check it>

Linear: <issue url>
```

Tick `[x]` only for checks you ran and saw pass on the code you pushed. Everything else is `[ ]` with the reason: not run, failed, or left for the reviewer. If nothing could be tested, say that in an unchecked item rather than leaving the section out.

## 7. Report

Keep it short: the issue, the branch (and the worktree path if you made one), the PR URL and whether it is a draft, which steps were already done and which you did now, the Testing list with anything left unchecked, and follow-ups. If everything was already shipped, say so.
