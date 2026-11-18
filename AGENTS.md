Each skill is a folder under `skills/`: a `SKILL.md`, plus `references/`, `scripts/` or `assets/` when it needs them.

- **Frontmatter**: `name` matches the folder name. `description` says what the skill does and when to use it. Slash-command skills add an `argument-hint`.
- **Invocation**: a skill is either user-invoked (`disable-model-invocation: true`, for anything that pushes, merges or spends a lot) or model-invoked (the description carries the trigger phrases).
- **README**: every skill has one line in `README.md`, under User-invoked or Model-invoked, with its name linked to its `SKILL.md`. Add, rename or remove the line with the skill.
- **Paths**: skills reference their own files as `~/.agents/skills/<name>/...`. `scripts/link-skills.sh` keeps those paths pointing into this repo; rerun it after adding or renaming a skill.
- **Portable**: settings for one repo (its Linear project, checks, login steps) belong in that repo's `.claude/skills/<name>/SKILL.md` overlay, not here.
- **Scripts**: standard library only where possible, so a skill works without an install step.
- **Writing**: imperative voice, short numbered sections. No em or en dashes; rewrite the sentence instead.
- **No secrets or people**: no tokens, passwords, customer data, or names and GitHub handles of colleagues in any file. A skill takes a reviewer from its arguments or a repo overlay.
