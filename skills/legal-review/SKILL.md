---
name: legal-review
description: Review a legal document (algemene voorwaarden or terms and conditions, SLA, DPA or verwerkersovereenkomst, privacy policy, NDA, any contract) against the actual law of its jurisdiction, using a council of AI models from different providers. They review independently, cross-examine each other's findings, and every cited article or ECLI is checked against the official text (wetten.overheid.nl, EUR-Lex, rechtspraak.nl) before a judge writes a ranked report with redlines and a list of missing clauses. Use when the user asks to review, check, audit or legally assess a contract or terms, asks whether clauses are enforceable or lawful, or wants a second opinion on legal wording, even without the word council. Use as /legal-review <file | url | pasted text>.
argument-hint: "<file | url | pasted text> [--council 2|3] [--rounds 1|2] [--jurisdiction NL] [--lang nl|en] [--for <party>]"
---

# Legal review council

Arguments: `$ARGUMENTS` (if that was not substituted, use the text after the skill name in the user's message).

- **Document**: a file path, a URL, or text pasted in the message.
- **`--council N`**: number of reviewers, default 2, at most one per available model vendor.
- **`--rounds N`**: debate rounds, 1 (default) or 2. Round 2 is a rebuttal round and only runs while material disputes remain.
- **`--jurisdiction XX`**: governing law, as an ISO country code or `EU`. Overrides what the document says, so confirm with the user if the two conflict.
- **`--lang nl|en`**: report language. Default: the language of the prevailing version of the document.
- **`--for <party>`**: whose interests the review serves. Default: the user's side, worked out in intake.

The council exists because one model's memory of the law is not a source. Three rules hold the whole way through:

- **The official text decides.** No article, lid or ECLI reaches the report until it has been fetched from an official source and read. A citation that cannot be checked is flagged as unverified, never presented as fact.
- **Reviewers stay independent until the debate.** Nobody sees another reviewer's output before submitting their own, and reviewers only see anonymous labels (A, B, C), never model names, so they argue with the reasoning and not the brand.
- **Disagreement is information.** The judge rules on disputes with reasons and keeps reasonable dissent visible instead of averaging it away.

`references/prompts.md` holds the briefs sent to reviewers. `references/sources.md` lists the official sources per jurisdiction. `scripts/cite.py` fetches the official text of a Dutch or EU provision, a Dutch ECLI or a CJEU judgment. `scripts/council.py` builds the briefs, tallies the disputes and collects the citations. Both scripts need only Python 3 and print their commands with `--help`.

## 1. Intake

**Load the document** into plain text with stable clause numbers, and save it as `document.md` in a work directory: the session's scratchpad directory when the system prompt names one, otherwise `$TMPDIR/legal-review/<slug>-<YYYYMMDD>/`. Never write into the user's repository or next to the document.

- **File**: read it. For code (TSX, JSX, MDX, HTML templates) keep only the visible text, with the article and lid numbers as the reader sees them. PDF and DOCX: extract the text (the pdf and docx skills cover this). Note the file's own "last amended" date if it has one.
- **URL**: fetch the raw page (`curl -sL` and strip the markup) rather than WebFetch, which summarises. If the page links a downloadable version (PDF), fetch that too and compare: two different versions in circulation is a finding in its own right.
- **Pasted text**: use it as given.
- **Several language versions**: find the clause that says which version prevails. Review the prevailing one in full and compare the others clause by clause for translation differences that change the meaning. No prevalence clause in a bilingual document is a finding.

**Establish the facts.** Derive what you can from the document and its surroundings (the site it is published on, the repo, the company), then ask the user, in one `AskUserQuestion` call, only what is still open:

- governing law and forum, from the choice-of-law and forum clauses. If the document is silent and the user does not know, ask. Never assume a jurisdiction from the language or the company's address alone, because consumer protection and mandatory rules follow other connections (for example a consumer's habitual residence).
- B2B, B2C or both. For B2B, the size of the counterparties if a rule depends on it.
- the document type, who drafted it, which party it protects, and whose interests this review serves (`--for`). Reviewing your own terms (make them hold up in court) is a different review from checking a supplier's (find what hurts you).
- how the document is used: incorporated in quotes, accepted with a click, published on a website, signed. Rules on incorporating general terms often depend on this.

When nobody can answer (an unattended or delegated run), go on with the open points written down as assumptions in `context.md` and in the report header. A jurisdiction is never one of them: without one, stop and ask.

Then state the scope in two lines before you start the council, for example: "Reviewing the Pixel Perfect algemene voorwaarden (Dutch law, B2B, drafted by and reviewed for Pixel Perfect, Dutch version prevails). Council: A, B; judge: this session; 1 round." When the skill was not started with `/legal-review` but picked up from a question, also say that this runs several models and ask before launching.

## 2. Pick the council

**In T3 Code** (`orchestrator_capabilities` and `delegate_task` exist, possibly as deferred tools to load first): call `orchestrator_capabilities` once.

- **Eligible providers** have `canRunCrossProviderChildTask: true`, no constraints, and at least one model.
- **Count vendors, not provider instances.** An ACP, proxy or second instance that serves Claude models is still Anthropic. Two seats from the same vendor are not two opinions.
- **Model per vendor**: its flagship, which is normally the first listed model. Skip names that mark a small or fast variant (fast, mini, nano, lite, flash, haiku). Set the provider's reasoning-effort option (its id varies: `reasoningEffort`, `effort`) to `high`, or the nearest value the list offers. Never take the max values unless the user asks; the debate rounds already multiply the cost.
- **Seat order**: fill seats with vendors other than the judge's own first, because the judge's vendor already gets its say when it rules. With `--council 3` and three vendors available, the third seat goes to the judge's vendor as a fresh child, which does not share the judge's context.
- **Fewer vendors than seats**: use what there is and say so in the report header. With one vendor only, use two of its different models (for example Opus and Sonnet) and call it a single-provider council.

**Without T3 Code**: use the native `Agent` tool with two different models (for example `opus` and `sonnet`) and say in the report header that the council was single-provider this time. Without any way to start subagents, review the document yourself, still verify every citation, and title the report "single-model review" instead of council.

Keep a private map from label to model (A = `gpt-6.1-sol` via Codex, and so on). It goes in the report header, never into reviewer briefs.

## 3. Independent reviews

Everything goes through files in the work directory, so that you never retype one reviewer's findings to show them to another. `scripts/council.py` does the bookkeeping:

1. Write `context.md` from the template in `references/prompts.md`, next to `document.md`.
2. `python3 ~/.agents/skills/legal-review/scripts/council.py brief <workdir> --round 0 --labels A,B --today "<date>" --lang <output language>` writes `brief-r0-<label>.md` per reviewer. Each brief names the output file `r0-<label>.json` that the reviewer must write.
3. Start all reviewers in one message, each with the short task from `references/prompts.md` that points at its brief: `delegate_task` with `role: "review"`, `mode: "async"`, the provider's `target` (`providerInstanceId`, `model`, `options`) and a title like `legal-review A: <document>`. Native `Agent` calls: send them in one message too.
4. The calls answer with `next`: end your turn; each completion wakes you. Do not poll. Tell the user in one line what is running, because a round can take from minutes to hours depending on the provider.
5. On each completion, use the reviewer's output file. Only if it is missing or invalid, take the JSON from `task_status`; a large result is saved to a file the tool names, so extract it with a script rather than reading or retyping it.

A reviewer that reports finding nothing has not done the job well: check that it read the whole document before counting its silence as agreement. When a result is unusable, start one replacement from another model or vendor, not a repeat. When one reviewer runs far longer than the others (in the dry run one provider took two hours for a round the others did in ten minutes), tell the user and offer to continue without it, but only while at least two reviewers remain.

## 4. Debate

**Round 1, cross-examination** (always). `council.py brief <workdir> --round 1` builds the briefs: the document, the reviewer's own findings, and the others' findings under their labels. Children keep no memory between tasks, so this is a new task per reviewer, started the same way as step 3. Each reviewer answers every finding of the others (agree, refine or challenge, with a reason), maintains, revises or withdraws its own, and may add issues everyone missed.

**Tally.** `council.py tally <workdir>` lists every finding with the verdicts on it and marks the open disputes. It also lists citation and reading objections, because reviewers often file a wrong citation under "refine" rather than "challenge". Merge duplicates first: three reviewers raising the same clause at different severities is one finding with a severity question, not three disputes.

**Round 2, rebuttal** (only with `--rounds 2`, and only for material disputes). A dispute is material when it changes whether a finding goes in the report, a severity at high or above, the legal basis or the redline, and the official text alone cannot settle it. Whether an article says what a reviewer claims is settled in step 5 by reading it, not by another round of argument. `council.py brief <workdir> --round 2 --disputed A3,B5` builds rebuttal briefs only for the authors of those findings; start only those. The author concedes or defends with something new. Skip the round when nothing material is left, and say so in the report.

## 5. Verify the law

Collect every citation that is still in play: the legal basis of surviving findings, the corrections offered in challenges, and anything you intend to cite yourself. Then check each one against the official text, never memory. `references/sources.md` says where to look per jurisdiction.

- **Dutch and EU legislation, Dutch and CJEU case law**: `council.py citations <workdir>` turns every citation in the round files into `citations.txt` (and lists what it could not parse in `citations-unparsed.txt`, to check by hand). Then `python3 ~/.agents/skills/legal-review/scripts/cite.py batch <workdir>/citations.txt > <workdir>/verify.txt` fetches them all in one call.
- **Other sources**: the official sites in `references/sources.md`, with WebFetch or `curl`. When WebFetch is the only route, ask it to quote the article text verbatim, and treat a page that will not load as unverified, not as confirmed.

**Read what comes back.** The batch only proves that the articles exist. Whether each one supports its proposition is your judgment, and reviewers' `self_checked: true` does not replace it: in the dry run a reviewer marked a real ECLI as checked and attached the wrong holding to it. Read the text for every citation that carries a finding of medium or above, and for every one a reviewer objected to. `cite.py` prints when the article's current text came into force; a date after the document's own date may mean the law changed under it, which is a finding in its own right. Compare with `cite.py nl <law> <article> --date <document date>` first: a new version date can also be an editorial change elsewhere in the article. An article that exists but says something else is a wrong citation. For each one, record:

- **verified**: the text exists and supports the proposition. Cite it with the pinpoint (lid, sub, sentence) and the version date.
- **corrected**: the proposition holds, but under a different article or lid you found and checked. Use the correct one and note the reviewer's error in the council log.
- **wrong**: the text does not support the proposition. Drop the basis; if the finding has no other basis left, drop the finding or mark it unverified.
- **unverified**: you could not reach the source. Keep the finding only if it stands without it, and label the citation as unverified.

**Case law** is cited only with an ECLI that the source confirms, and only when the court, the date and the summary match what the reviewer claimed. The ECLI existing is not enough: a real ECLI from the wrong case is a common failure. Case names without an ECLI ("Haviltex", "Saladin/HBU") are kept as context only once you have found and checked their ECLI.

**Claims about doctrine** ("settled case law", "the prevailing view") without a checkable source are presented as the reviewer's view, not as law.

## 6. Verdict

You are the judge. Your job is to rule, not to count votes.

- **Merge** findings about the same clause and the same problem into one, noting which reviewers raised it.
- **Rule on each dispute** with reasons grounded in the verified text and the facts of the document. When the losing side had a reasonable, verified argument, keep it visible as dissent in one sentence.
- **Add** issues you found yourself while verifying, labelled as raised by the judge. Do not add more than a reviewer could have defended.
- **Agreement level** per finding: `unanimous` (raised or agreed by all), `majority`, `split` (you ruled between opposed views), `single` (one reviewer, unchallenged), `judge` (raised by you).
- **Severity**: `critical` (likely void or unenforceable on a core point, or exposure to large liability or a regulatory fine), `high` (likely to fail or cost real money when tested), `medium` (weakens the position, or an ambiguity a court may read against the drafter), `low` (drafting quality, consistency). When the severity hinges on a fact nobody could confirm (how the terms are incorporated, whether a separate DPA exists), rate what is known and say in the problem what would make it worse.
- **Findings first raised in round 1** were never cross-examined. Weigh them yourself and say so in the agreement line.
- **Missing clauses**: a short list of what the document lacks for its type and the reviewed party (for example a liability cap with an amount, a DPA, retention of title, an acceptance procedure). Each item says why it matters, in one line.

Write the report in the output language, quoting clauses in the document's own language. Rank findings by severity. Take every link from the verification output (`verify.txt`); never type a URL from memory. Save it as `report.md` in the work directory and print it in the chat; when it is long, print the summary and the top findings and give the path. Use this template:

```markdown
# Legal review: <document name> (<version or date>)

<Jurisdiction> law, <B2B/B2C>, <document type>, drafted by <party>, reviewed for <party>. Prevailing version: <language>.
Council: A = <model> (<provider>), B = <model> (<provider>)[, C = ...]. Judge: <model>. Debate rounds: <n>.[ Single-provider council: <reason>.]
Not legal advice: have a lawyer review the final text before you rely on it.

## Summary
<Three to five sentences: overall state, the most serious problems, the biggest gap.>

## Findings

### 1. [critical] <short title> (art. <x.y>)
- **Clause**: "<quote>"
- **Problem**: <what is wrong and what happens if it is tested>
- **Legal basis**: art. 6:233 sub a BW ([wetten.overheid.nl](<url>), version <date>); ECLI:NL:HR:... (<court>, <date>)
- **Redline**: <replacement text in the document's language, or "delete">
- **Agreement**: <level>. <Dissent or ruling in one sentence, if any.>

## Missing from the document
- **<topic>**: <why it matters>[, legal basis if any]

## Unverified or rejected citations
- <citation>: <who cited it, what was wrong or why it could not be checked>

## Council log
<Per finding that changed during the debate: who challenged what, who conceded. Short. Leave out findings everyone agreed on.>
```

Then offer to apply the redlines: to the document itself when the user owns and can edit it, or as a redlined copy in the work directory. Ask first; never edit a document the user called read-only or that lives in a repository another task is working in.

## 7. Report back

In the chat: the path to `report.md`, the council composition, the top findings, the missing clauses, how many citations were verified, corrected, rejected or left unverified, and the offer to apply the redlines.
