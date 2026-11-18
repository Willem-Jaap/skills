#!/usr/bin/env python3
"""Bookkeeping for a legal review council: build briefs, tally disputes, list citations.

  council.py brief <workdir> --round 0 --labels A,B[,C] --today "<date>" --lang <language>
  council.py brief <workdir> --round 1
  council.py brief <workdir> --round 2 --disputed A3,B5
  council.py tally <workdir>
  council.py citations <workdir>

The work directory holds context.md and document.md (written in intake). Briefs are
written as brief-r<round>-<label>.md and name the output file r<round>-<label>.json that
the reviewer must write. Templates come from ../references/prompts.md.

`tally` prints every finding with the other reviewers' verdicts and the author's own
response, and marks the open disputes. `citations` turns every citation in the round
files into cite.py batch lines (citations.txt) and lists the ones it could not parse
(citations-unparsed.txt) so they are checked by hand.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = os.path.join(HERE, "..", "references", "prompts.md")
EMBED_LIMIT = 150_000  # characters; above this the brief points at document.md instead


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def template(name):
    text = open(PROMPTS, encoding="utf-8").read()
    m = re.search(r"## " + re.escape(name) + r"\n.*?````text\n(.*?)\n````", text, re.S)
    if not m:
        die(f"template {name!r} not found in {PROMPTS}")
    return m.group(1)


def load_json(path):
    raw = open(path, encoding="utf-8").read().strip()
    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.S)
    if fenced:
        raw = fenced.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON ({e}). Fix the file or save the reviewer's reply into it.")


def settings(work, update=None):
    path = os.path.join(work, "council.json")
    cfg = json.load(open(path)) if os.path.exists(path) else {}
    if update:
        cfg.update({k: v for k, v in update.items() if v})
        json.dump(cfg, open(path, "w"), indent=2)
    return cfg


def fill(text, values):
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", str(v))
    left = re.findall(r"\{\{\w+\}\}", text)
    if left:
        die(f"unfilled placeholders: {sorted(set(left))}")
    return text


def round_file(work, r, label):
    return os.path.join(work, f"r{r}-{label}.json")


def findings_by_id(work, labels):
    """Latest version of every finding: round 0, replaced by a round 1 revision, plus round 1 new findings."""
    out = {}
    for L in labels:
        r0 = load_json(round_file(work, 0, L))
        for f in r0.get("findings", []):
            out[f["id"]] = dict(f, _author=L, _round=0)
        p1 = round_file(work, 1, L)
        if os.path.exists(p1):
            r1 = load_json(p1)
            for o in r1.get("own", []):
                if o.get("id") in out:
                    out[o["id"]]["_action"] = o.get("action")
                    out[o["id"]]["_action_reasons"] = o.get("reasons", "")
                    if o.get("action") == "revise" and isinstance(o.get("revised"), dict) and o["revised"].get("issue"):
                        out[o["id"]] = dict(o["revised"], id=o["id"], _author=L, _round=1, _action="revise",
                                            _action_reasons=o.get("reasons", ""))
            for f in r1.get("new_findings", []):
                out[f["id"]] = dict(f, _author=L, _round=1, _new=True)
    return out


def responses(work, labels):
    """target id -> list of (label, response) from round 1."""
    out = {}
    for L in labels:
        p1 = round_file(work, 1, L)
        if os.path.exists(p1):
            for resp in load_json(p1).get("responses", []):
                out.setdefault(resp.get("target"), []).append((L, resp))
    return out


def brief(work, rnd, labels=None, today=None, lang=None, disputed=None):
    cfg = settings(work, {"labels": labels, "today": today, "lang": lang})
    labels = cfg.get("labels")
    if not labels:
        die("pass --labels A,B[,C] on round 0")
    for k in ("today", "lang"):
        if not cfg.get(k):
            die(f"pass --{k} on round 0")
    context = open(os.path.join(work, "context.md"), encoding="utf-8").read().strip()
    doc_path = os.path.join(work, "document.md")
    doc = open(doc_path, encoding="utf-8").read().strip()
    if len(doc) > EMBED_LIMIT:
        doc = f"The document is long. Read it in full from {doc_path}."
    rules = fill(template("Rules"), {"today": cfg["today"], "language": cfg["lang"]})
    base = {"n": len(labels), "context": context, "rules": rules, "document": doc, "round": rnd}
    written = []
    for L in labels:
        values = dict(base, label=L, output_path=round_file(work, rnd, L))
        if rnd == 0:
            text = fill(template("Reviewer brief"), values)
        elif rnd == 1:
            own = json.dumps(load_json(round_file(work, 0, L)), ensure_ascii=False, indent=2)
            others = "\n\n".join(
                f"### Reviewer {o}\n\n```json\n" + json.dumps(load_json(round_file(work, 0, o)), ensure_ascii=False, indent=2) + "\n```"
                for o in labels if o != L)
            text = fill(template("Cross-examination brief"), dict(values, own=f"```json\n{own}\n```", others=others))
        else:
            if not disputed:
                die("round 2 needs --disputed <ids>: the material disputes you want rebutted")
            mine = [i for i in disputed if i.startswith(L)]
            if not mine:
                continue
            fs, rs = findings_by_id(work, labels), responses(work, labels)
            parts = []
            for i in mine:
                f = {k: v for k, v in fs.get(i, {}).items() if not k.startswith("_")}
                chal = [f"- Reviewer {who}: {r.get('verdict')} ({r.get('defect') or 'no defect named'}). {r.get('reasons', '')}"
                        + (f" Correct citation offered: {r['correct_citation']}." if r.get("correct_citation") else "")
                        + (f" Suggested severity: {r['suggested_severity']}." if r.get("suggested_severity") else "")
                        for who, r in rs.get(i, []) if r.get("verdict") in ("challenge", "refine")]
                parts.append(f"### {i}\n\n```json\n{json.dumps(f, ensure_ascii=False, indent=2)}\n```\n\nChallenges:\n" + "\n".join(chal or ["- (none recorded)"]))
            text = fill(template("Rebuttal brief"), dict(values, challenged="\n\n".join(parts)))
        path = os.path.join(work, f"brief-r{rnd}-{L}.md")
        open(path, "w", encoding="utf-8").write(text)
        written.append((L, path, len(text)))
    for L, path, n in written:
        print(f"{L}: {path} ({n} chars) -> writes {round_file(work, rnd, L)}")


SEV = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def tally(work):
    labels = settings(work).get("labels") or die("no council.json; run `brief --round 0` first")
    fs, rs = findings_by_id(work, labels), responses(work, labels)
    rebut = {}
    for L in labels:
        for r in (2, 3):
            p = round_file(work, r, L)
            if os.path.exists(p):
                for b in load_json(p).get("rebuttals", []):
                    rebut[b.get("id")] = b
    open_disputes, to_verify = [], []
    for i, f in fs.items():
        resp = rs.get(i, [])
        verdicts = ", ".join(f"{who}:{r.get('verdict')}" + (f"/{r.get('defect')}" if r.get("defect") else "")
                             + (f"/sev={r.get('suggested_severity')}" if r.get("suggested_severity") else "") for who, r in resp)
        sevs = [SEV.get(str(r.get("suggested_severity", "")).lower()) for _, r in resp if r.get("suggested_severity")]
        sev_gap = any(s and abs(s - SEV.get(f.get("severity", ""), 0)) >= 2 for s in sevs)
        challenged = any(r.get("verdict") == "challenge" for _, r in resp)
        # A "refine" can still say the citation is wrong or the clause misread: the judge must settle those.
        objections = [f"{who}: {r.get('defect')}" + (f" (offers {r['correct_citation']})" if r.get("correct_citation") else "")
                      for who, r in resp if r.get("defect") in ("wrong_citation", "misread_clause", "not_applicable")]
        action = f.get("_action", "new in round 1, not cross-examined" if f.get("_new") else "no response")
        conceded = action in ("withdraw",) or rebut.get(i, {}).get("action") == "concede"
        status = "withdrawn" if action == "withdraw" else ("OPEN" if (challenged or sev_gap) and not conceded else "")
        if status == "OPEN":
            open_disputes.append(i)
        print(f"{i} [{f.get('severity')}] {f.get('clause')}: {str(f.get('issue', ''))[:110]}")
        print(f"    author {f['_author']}: {action}" + (f"; rebuttal: {rebut[i].get('action')}" if i in rebut else ""))
        print(f"    others: {verdicts or '-'}" + (f"   ** {status}" if status else ""))
        if objections and action != "withdraw":
            print(f"    check in verification: {'; '.join(objections)}")
            to_verify.append(i)
    print(f"\nopen disputes ({len(open_disputes)}): {', '.join(open_disputes) or 'none'}")
    print(f"citation or reading objections to settle in verification ({len(to_verify)}): {', '.join(to_verify) or 'none'}")
    print("Merge duplicates first, then decide which open disputes are material: they change inclusion, a severity of")
    print("high or above, the legal basis or the redline, and the official text alone cannot settle them.")


DUTCH_LAWS = {"Overgangswet": "OBW", "BW": None, "Rv": "Rv", "Aw": "Aw", "Auteurswet": "Aw", "UAVG": "UAVG", "Fw": "Fw",
              "Faillissementswet": "Fw", "Handelsnaamwet": "HNW", "Handelsregisterwet": "HRW", "Mededingingswet": "MW",
              "AWR": "AWR", "Wbb": "WBB", "Telecommunicatiewet": "Tw", "Tw": "Tw"}
EU_NAMES = {"AVG": "GDPR", "GDPR": "GDPR", "Dataverordening": "DATA-ACT", "Data Act": "DATA-ACT", "AI-verordening": "AI-ACT",
            "AI Act": "AI-ACT", "DSA": "DSA", "NIS2": "NIS2"}


QUALIFIERS = re.compile(
    r"\b(lid|leden|sub|onder|punt|alinea|aanhef|paragraph|para|point|sentence|zin)\b\.?\s*(?:\d+[a-z]?|[a-z]{1,2})\b(?!:)"
    r"(?:\s*(?:-|,|en|and|t/m|tot en met)\s*(?:\d+[a-z]?|[a-z]{1,2})\b(?!:))*", re.I)
ARTS = re.compile(r"\bart(?:ikel|icle)?s?\.?\s*((?:\d+[a-z]?:)?\d+[a-z]?(?:\s*(?:,|en|and|&)\s*(?:\d+[a-z]?:)?\d+[a-z]?)*)", re.I)


def eu_celex(seg):
    """CELEX for 'Verordening (EU) 2016/679', 'Regulation (EU) No 1215/2012' or 'Richtlijn 2009/24/EG'."""
    m = re.search(r"(Verordening|Richtlijn|Regulation|Directive)\s*(?:\((?:EU|EG|EEG|EC|EEC)\)\s*)?(?:nr\.?|No\.?)?\s*(\d{1,4})/(\d{1,4})", seg, re.I)
    if not m:
        return None
    kind, a, b = m.group(1).lower(), int(m.group(2)), int(m.group(3))
    # 2016/679 and 2009/24/EG put the year first; the pre-2015 "No 1215/2012" puts it last.
    year, num = (b, a) if not 1950 <= a <= 2099 and 1950 <= b <= 2099 else (a, b)
    if year < 100:
        year += 1900 if year > 50 else 2000
    return f"3{year}{'R' if kind in ('verordening', 'regulation') else 'L'}{num:04d}"


def parse_citation(c):
    """Return cite.py batch lines for one citation string, or [] if it cannot be parsed."""
    lines = []
    for m in re.finditer(r"ECLI:[A-Z]{2}:[A-Z0-9]+:\d{4}:[A-Z0-9.]+", c):
        lines.append(f"ecli {m.group(0)}")
    for m in re.finditer(r"\b([CT])[-\u2011](\d{1,4})/(\d{2})\b", c):
        lines.append(f"cjeu {m.group(1)}-{m.group(2)}/{m.group(3)}")
    for seg in re.split(r";", c):
        clean = QUALIFIERS.sub(" ", seg)
        arts = [a.strip() for m in ARTS.finditer(clean) for a in re.split(r"\s*(?:,|\ben\b|\band\b|&)\s*", m.group(1)) if a.strip()]
        if not arts:
            continue
        celex = eu_celex(seg)
        eu_alias = next((alias for name, alias in EU_NAMES.items() if re.search(r"\b" + re.escape(name) + r"\b", seg)), None)
        nl_alias = next((alias for name, alias in DUTCH_LAWS.items() if alias and re.search(r"\b" + re.escape(name) + r"\b", seg)), None)
        bw = re.search(r"\bBW\b|Burgerlijk Wetboek", seg) and not re.search(r"Overgangswet", seg)
        for a in arts:
            if ":" in a and bw:
                lines.append(f"nl BW {a}")
            elif celex:
                lines.append(f"eu {celex} {a}")
            elif eu_alias:
                lines.append(f"eu {eu_alias} {a}" + (" --lang nl" if eu_alias in ("GDPR", "DATA-ACT", "AI-ACT") and re.search(r"AVG|verordening", seg, re.I) else ""))
            elif nl_alias:
                lines.append(f"nl {nl_alias} {a}")
    return lines


def citations(work):
    labels = settings(work).get("labels") or die("no council.json; run `brief --round 0` first")
    seen, unparsed = {}, {}

    def add(c, who):
        if not c:
            return
        lines = parse_citation(c)
        if not lines:
            unparsed.setdefault(c, set()).add(who)
        for line in lines:
            seen.setdefault(line, set()).add(who)

    def walk(obj, who):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("citation", "correct_citation") and isinstance(v, str):
                    add(v, who)
                else:
                    walk(v, who)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, who)

    for name in sorted(os.listdir(work)):
        m = re.fullmatch(r"r(\d)-([A-Z])\.json", name)
        if m:
            walk(load_json(os.path.join(work, name)), f"{m.group(2)}{'' if m.group(1) == '0' else '@r' + m.group(1)}")
    with open(os.path.join(work, "citations.txt"), "w", encoding="utf-8") as f:
        for line in sorted(seen):
            f.write(f"{line}\n")
    with open(os.path.join(work, "citations-unparsed.txt"), "w", encoding="utf-8") as f:
        for c in sorted(unparsed):
            f.write(f"{c}    # cited by {', '.join(sorted(unparsed[c]))}\n")
    print(f"{len(seen)} checkable lines -> {os.path.join(work, 'citations.txt')}")
    print(f"{len(unparsed)} unparsed -> {os.path.join(work, 'citations-unparsed.txt')} (check these by hand)")
    print(f"next: python3 {os.path.join(HERE, 'cite.py')} batch {os.path.join(work, 'citations.txt')}")


def main(argv):
    if len(argv) < 3 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, work = argv[1], os.path.abspath(argv[2])
    opts, it = {}, iter(argv[3:])
    for a in it:
        if a.startswith("--"):
            opts[a[2:]] = next(it, None)
    if cmd == "brief":
        brief(work, int(opts.get("round", 0)),
              labels=opts["labels"].split(",") if opts.get("labels") else None,
              today=opts.get("today"), lang=opts.get("lang"),
              disputed=opts["disputed"].split(",") if opts.get("disputed") else None)
    elif cmd == "tally":
        tally(work)
    elif cmd == "citations":
        citations(work)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
