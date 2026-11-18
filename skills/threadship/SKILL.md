---
name: threadship
description: Start the ship flow for a Linear issue in a new T3 Code thread with its own worktree, so the current thread stays free. Use as /threadship PIX-123 or /threadship <linear issue url>; several issues get one thread each.
argument-hint: "[PIX-123 | linear issue url]... [--ready] [reviewer] [notes]"
disable-model-invocation: true
---

# Threadship

Arguments: `$ARGUMENTS` (if that was not substituted, use the text after the skill name in the user's message).

Start the ship skill (`~/.agents/skills/ship/SKILL.md`) for each issue in a new T3 Code thread, each in its own fresh worktree, then hand back. This thread does not implement anything itself.

This needs T3 Code. Load `t3_thread_launch` (with ToolSearch when T3 tools are deferred). If it is not available, say so, suggest `/ship` in this thread instead, and stop.

## 1. Parse

- **Issues**: every `[A-Z]+-[0-9]+` in the arguments, bare (`PIX-2481`) or inside Linear URLs, without duplicates. None given: ask which issue to ship.
- **Everything else** (`--ready`, a reviewer handle, notes) is passed through unchanged to every ship run.
- More than 4 issues: show the list and confirm before launching.

## 2. Look up each issue

For every issue, in parallel:

- **Linear** `get_issue`: identifier, title, url, `gitBranchName`, project, state. Skip a Done or Canceled issue and say so.
- **T3 project**: the current thread's project by default. If the issue's Linear project clearly belongs to another repo, find that repo's project in `t3_project_list` by its repository name. Prefer the main clone over worktree checkouts (paths under `.t3/worktrees`, `.claude/worktrees` or named `<repo>-pix-*`). Ask when it is unclear.
- **Base branch**, in that project's root: `git -C <root> fetch origin --prune`, then `git -C <root> symbolic-ref --short refs/remotes/origin/HEAD` minus `origin/`, falling back to `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`.
- **Existing work**:
  - `git -C <root> worktree list`: is `gitBranchName` checked out somewhere?
  - `git -C <root> ls-remote --heads origin <gitBranchName>` and `git -C <root> rev-parse --verify --quiet refs/heads/<gitBranchName>`: does the branch exist?
  - `t3_thread_search` for the identifier: is a thread already shipping it? If one is active, give its link and skip the issue unless the user asked for a new thread anyway.

## 3. Launch one thread per issue

Call `t3_thread_launch` once per issue, all in the same message:

- **title**: `<PIX-123> <issue title>`, shortened to about 60 characters.
- **projectId**: leave it out for the current project, otherwise the project found in step 2.
- **workspaceStrategy**:
  - The branch does not exist anywhere: `{ type: "worktree", baseRef: "<base>", branch: "<gitBranchName>", startFromOrigin: true }`.
  - The branch exists but is not checked out: `{ type: "worktree", baseRef: "<base>", startFromOrigin: true }` without `branch`. Ship then switches the new checkout to the existing branch.
  - The branch is checked out in a project worktree: `{ type: "existing_worktree", worktreePath: "<path>" }`, or `{ type: "root" }` when that is the project's main checkout.
- **Model, runtime and interaction modes**: leave them out so the thread inherits this one's.
- **clientRequestId**: `threadship-<identifier>-<YYYYMMDDHHmm>`, reused when retrying the same launch.
- **message**:

  ```text
  Ship <PIX-123>: <issue title>
  <issue url>

  Read ~/.agents/skills/ship/SKILL.md and follow it end to end for this issue, with these arguments: <PIX-123> <pass-through arguments>

  /threadship started this thread in a fresh worktree from origin/<base>.
  ```

  The message points at the skill file instead of sending `/ship`. Ship can only be started by a person typing the command, and a provider may not expand a slash command that arrives through a tool.

If a launch errors or its reply is lost, retry once with the same `clientRequestId`. If the worktree strategy fails because the branch already exists, retry without `branch`.

## 4. Report

One line per issue: the thread's `link` exactly as returned, the branch, and whether it reused an existing worktree. List skipped issues with the reason. Do not wait on or poll the new threads: each one runs interactively, so ship's questions show up in that thread and the user follows it there.
