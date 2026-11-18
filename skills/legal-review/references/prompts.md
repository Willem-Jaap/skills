# Council briefs

`scripts/council.py` fills in these templates and writes one brief per reviewer per round into the work directory. You write `context.md` (from the template below) and `document.md`; the script adds the rules, the document, the findings and the output path. Edit the templates here, not in the script.

Each child then gets a short task that points at its brief:

```text
You are Reviewer <label> on a legal review council. Your complete brief, including the document, is in <absolute path of the brief>. Read the whole file and follow it exactly. Write your result to the output file the brief names, then reply with the same JSON. If you cannot read the brief, reply only with "CANNOT READ BRIEF" and the error.
```

Files keep the briefs out of the orchestrator's own output (the document alone can be tens of thousands of characters, sent once per reviewer per round), and every answer lands in a file, so no one has to retype one reviewer's findings to show them to another. Children start with no history, so every brief carries the context and the document in full. Model and provider names never appear in a brief: reviewers know each other only as A, B and C.

## Contents

- Context (`context.md`, written by you in intake)
- Reviewer brief (round 0)
- Cross-examination brief (round 1)
- Rebuttal brief (round 2 and later)
- Rules (added to every brief)

## Context

Write this to `context.md` in the work directory. Every brief includes it unchanged.

```text
- Document: <document type>, "<title>", <version or date>
- Governing law: <law>. Forum: <forum>.
- Relationship: <B2B / B2C / both>. <counterparty notes, e.g. "clients are mostly SMEs">
- Drafted by: <drafter>. Protects: <party>. This review serves: <party>, whose goal is <goal>.
- How the document is used: <e.g. "published on the website and referenced in quotes">
- Language: <prevailing version>. <other versions and the prevalence clause, if any>
- Facts from intake: <anything the user said or you established, such as a second version in circulation>
- Assumptions: <facts nobody could confirm, stated as assumptions>
```

## Reviewer brief

````text
You are Reviewer {{label}} on a legal review council. {{n}} reviewers, each a different AI model, review the same document independently. Afterwards you will cross-examine each other's findings, and a judge will check every citation against the official legal text. Citations that turn out to be invented or wrong are struck from the report and noted against the reviewer who made them, so cite only what you are sure of, and say so when you are not.

## Context

{{context}}

## Task

1. Read the whole document below. Do not skim: the judge will notice findings that depend on a clause you did not read.
2. Find what matters for the party this review serves:
   - clauses that are void, voidable, unenforceable, or contrary to mandatory law;
   - clauses that are internally inconsistent, contradict each other, or use undefined terms;
   - wording a court would likely read against the drafter;
   - translation differences between language versions that change the meaning;
   - commercial risks the clause creates for the served party, including clauses that work against the drafter's own interests;
   - recent or pending changes in the law that affect a clause;
   - important clauses that are missing for this kind of document.
3. Give each finding its legal basis as a pinpoint citation in the jurisdiction's standard form: for Dutch law "art. 6:233 sub a BW", "art. 7:408 lid 1 BW", "art. 241 Rv", "art. 28 lid 3 AVG". Case law only with its ECLI. If you know the rule but not the exact article, write that in `basis_note` instead of guessing a number.
4. Check your citations if you can run shell commands: `python3 ~/.agents/skills/legal-review/scripts/cite.py nl BW 6:233`, `... eu GDPR 28 --lang nl`, `... ecli ECLI:NL:HR:1981:AG4158` (`--help` lists more; `batch <file>` checks a list in one call). Mark a citation `self_checked: true` only when you read the official text and it supports your point.
5. One finding per problem. When two clauses share a problem, make one finding that names both; when one clause has two unrelated problems, make two.

{{rules}}

## Output

Write your result as JSON to {{output_path}}, then reply with the same JSON in one fenced block and nothing after it. Use this shape:

```json
{
  "reviewer": "{{label}}",
  "findings": [
    {
      "id": "{{label}}1",
      "clause": "art. 8.1",
      "quote": "the exact words the finding is about, in the document's language",
      "issue": "what is wrong and what happens when it is tested",
      "legal_basis": [
        {"citation": "art. 6:233 sub a BW", "proposition": "what this provision says that supports the issue", "self_checked": true}
      ],
      "basis_note": "optional: a principle you rely on without an exact citation",
      "severity": "critical | high | medium | low",
      "redline": "replacement text in the document's language, or \"delete\"",
      "confidence": "high | medium | low"
    }
  ],
  "missing": [
    {"topic": "liability cap with an amount", "why": "one line", "legal_basis": [], "suggested_clause": "text in the document's language"}
  ],
  "assumptions": ["facts you assumed that the context did not give"]
}
```

Severity: `critical` = likely void or unenforceable on a core point, or exposure to large liability or a regulatory fine; `high` = likely to fail or cost real money when tested; `medium` = weakens the position, or an ambiguity a court may read against the drafter; `low` = drafting quality and consistency.

## Document

{{document}}
````

## Cross-examination brief

````text
You are Reviewer {{label}} on a legal review council, in round 1 of the debate. Earlier, {{n}} reviewers reviewed the document below independently. You now see your own findings and the other reviewers' findings. A judge will rule on every dispute after checking the cited law against the official text.

## Context

{{context}}

## Task

1. For every finding by another reviewer, give a verdict:
   - `agree`: right, with the right basis and severity.
   - `refine`: right in substance, but the citation, severity or redline needs a change. Say exactly what.
   - `challenge`: wrong. Name the defect as one of `wrong_citation` (the article does not say that, does not exist, or is the wrong lid), `misread_clause`, `not_applicable` (for example a consumer-only rule applied to B2B, or the wrong jurisdiction), `overstated_risk`, `understated_risk`, `bad_redline`, `duplicate`. Give your reasons and, where you can, the correct citation.
   Do not invent disagreement to look useful, and do not agree to be polite. Check a citation before you challenge it (`python3 ~/.agents/skills/legal-review/scripts/cite.py ...`).
2. For each of your own findings: `maintain`, `revise` (give the full new version) or `withdraw`, with one line of reasons. Withdraw what the others showed to be wrong.
3. Add issues that every reviewer missed, as new findings in the reviewer format, with ids `{{label}}N1`, `{{label}}N2`, ...

{{rules}}

## Output

Write your result as JSON to {{output_path}}, then reply with the same JSON in one fenced block. Use this shape:

```json
{
  "reviewer": "{{label}}",
  "responses": [
    {"target": "B3", "verdict": "agree | refine | challenge", "defect": "wrong_citation | misread_clause | not_applicable | overstated_risk | understated_risk | bad_redline | duplicate | null", "reasons": "...", "correct_citation": "optional", "suggested_severity": "optional", "suggested_redline": "optional"}
  ],
  "own": [
    {"id": "{{label}}2", "action": "maintain | revise | withdraw", "reasons": "...", "revised": {"optional": "the full finding in the reviewer format"}}
  ],
  "new_findings": []
}
```

## Your findings

{{own}}

## The other reviewers' findings

{{others}}

## Document

{{document}}
````

## Rebuttal brief

````text
You are Reviewer {{label}} on a legal review council, in round {{round}} of the debate. Other reviewers challenged some of your findings, and the judge considers these disputes material. The judge will rule on each one after checking the cited law against the official text.

## Context

{{context}}

## Task

For each challenged finding below: `concede`, `partially_concede` (give the revised finding) or `defend`. Defend only with something new: a better reading of the clause, a checked citation, a fact the challenger missed. Repeating your first argument does not count, and the judge will treat it as a concession. No new findings in this round.

{{rules}}

## Output

Write your result as JSON to {{output_path}}, then reply with the same JSON in one fenced block. Use this shape:

```json
{
  "reviewer": "{{label}}",
  "rebuttals": [
    {"id": "{{label}}3", "action": "concede | partially_concede | defend", "reasons": "...", "revised": {"optional": "the full finding in the reviewer format"}}
  ]
}
```

## Your challenged findings and the challenges

{{challenged}}

## Document

{{document}}
````

## Rules

````text
Rules:
- Read only, apart from your one output file. Do not edit or delete anything else, and do not run anything that changes state. Shell commands are for reading the law (cite.py keeps its own cache, which is fine).
- Apply the law of the governing jurisdiction as in force today ({{today}}). If a rule changed recently or a change is pending, say so and give both.
- Rules that protect only consumers do not apply directly in B2B. If you rely on them indirectly (for example a reflex effect that courts give consumer blacklists in contracts with small businesses), say that you do and why it applies to these parties.
- Distinguish what the law says from what you think a court would do. Mark the second as your assessment.
- No invented articles, case names or ECLIs. An honest "I believe there is a rule here but cannot cite it" is worth more than a confident wrong number.
- Quote the document exactly. Refer to clauses by the numbering the document itself uses.
- Write in {{language}}; quote the document and write redlines in the document's own language.
````
