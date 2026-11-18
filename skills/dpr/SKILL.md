---
name: dpr
description: Open a draft PR for the work already in this checkout, following the ship skill's rules for branch, commit, screenshots and PR description (what, why, how, and a checkbox list of what was tested). Does not implement anything. Use as /dpr, optionally with an issue (PIX-123 or a Linear URL), a reviewer or notes.
argument-hint: "[PIX-123 | linear issue url] [reviewer] [notes]"
disable-model-invocation: true
---

# Draft PR

Arguments: `$ARGUMENTS` (if that was not substituted, use the text after the skill name in the user's message). They may name an issue, a reviewer and notes for the description, parsed as in the ship skill. There is no `--ready`: this PR is always a draft.

Read `~/.agents/skills/ship/SKILL.md` and follow it for the current work, with the changes below. The work is already done, so this is ship without the implementation.

## What counts as the current work

The uncommitted changes in this checkout plus any commits on the current branch that are not on `origin/<base>`. If none of either, say there is nothing to open a PR for and stop.

Take all of it by default. If part of it clearly does not belong (stray debug files, unrelated edits, a second feature), ask which files go in. Never commit `.env` files or secrets.

## How the ship steps change

1. **Read the repo and the issue**: as in ship. The issue comes from the arguments or the current branch name. With neither, create one from the diff as ship describes. If the repo has no Linear project at all (a personal repo), skip the issue: name the branch `<type>/<short-kebab-summary>` and leave the Linear line out of the PR body.
2. **Start from the latest base**: keep the work, never discard or overwrite any of it.
   - Already on the issue's branch: stay, as in ship.
   - On the base branch with uncommitted changes: carry them to a new branch from `origin/<base>` (ship's stash, switch, pop).
   - Commits made on the local base branch: `git switch -c <branch>` so they come along, `git rebase origin/<base>`, and only then move the local base back with `git branch -f <base> origin/<base>`.
   - On some other branch: ask whether the work belongs to that branch's issue or to a new branch.
3. **Implement**: skip it. Do not change the code beyond what the repo's formatters fix automatically.
4. **Verify**: run the repo's checks for the touched paths and exercise the change where you can, as in ship. A failing check is not yours to fix here: tell the user, and ask whether to stop or open the PR with it listed unchecked.
5. **Screenshots**: as in ship for UI changes. The code is already changed, so for **before** shots use the same page on production or staging, or a temporary detached worktree of `origin/<base>` when the app runs from one. Never stash the work to get a before shot. If neither is practical, show after only and say so in the PR.
6. **Commit, push, PR**: as in ship, always as a draft. If a PR already exists for the branch, update its body instead of opening another.
7. **Report**: as in ship.
