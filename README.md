# Skills

My agent skills. They work in Claude Code, Codex and other harnesses that read [Agent Skills](https://agentskills.io).

## Install

```bash
npx skills add Willem-Jaap/skills
```

Or clone and link them, so a `git pull` updates every installed skill:

```bash
git clone https://github.com/Willem-Jaap/skills ~/Code/skills
~/Code/skills/scripts/link-skills.sh
```

## Skills

### User-invoked

These run only when you type them (`disable-model-invocation: true`).

- **[ship](skills/ship/SKILL.md)**: Ship a Linear issue end to end: branch from the latest default branch, implement, verify, and open a draft PR with screenshots and a checklist of what was tested.
- **[threadship](skills/threadship/SKILL.md)**: Start `/ship` in a new T3 Code thread with its own worktree, one thread per issue.
- **[dpr](skills/dpr/SKILL.md)**: Open a draft PR for the work already in the checkout, following ship's rules for branch, commit and description.
- **[dependabot](skills/dependabot/SKILL.md)**: Triage open Dependabot PRs: merge the safe ones, rebase the stale ones, and refuse the rest with a reason.
- **[eyesupgrade](skills/eyesupgrade/SKILL.md)**: Upgrade the Eyes SDKs in every project that uses them, with one PR per repo.

### Model-invoked

The model can pick these up by itself, and you can type them too.

- **[legal-review](skills/legal-review/SKILL.md)**: Review a contract or terms against the actual law with a council of models from different providers that argue with each other. Every citation is checked against the official text.
- **[css-clamp](skills/css-clamp/SKILL.md)**: Generate fluid CSS `clamp()` values for type, spacing and layout with a bundled calculator, for plain CSS, custom properties and Tailwind.
