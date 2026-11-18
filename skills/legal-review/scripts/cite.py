#!/usr/bin/env python3
"""Fetch the official text of a cited provision or court decision, so a citation
can be checked against the source instead of memory.

  cite.py nl <law> <article> [--date YYYY-MM-DD]   Dutch law, wetten.overheid.nl
  cite.py eu <act> <article> [--lang en|nl|de|fr]  EU act, Publications Office (EUR-Lex text)
  cite.py ecli <ECLI>                              Dutch court decision, rechtspraak.nl open data
  cite.py cjeu <C-123/45> [--lang en|nl]           CJEU judgment by case number, Publications Office
  cite.py find <title words>                       find a Dutch law's BWBR id by title
  cite.py batch [file]                             one of the commands above per line (stdin if no file)
  cite.py laws                                     list the known aliases

Examples:
  cite.py nl BW 6:233          cite.py nl BW7 404       cite.py nl Rv 241
  cite.py nl Aw 2              cite.py nl BWBR0005289 233
  cite.py eu GDPR 28 --lang nl cite.py eu 32023R2854 13
  cite.py ecli ECLI:NL:HR:1981:AG4158

Exit codes: 0 found, 2 article or decision not found, 3 source unreachable or
unknown law. Standard library only. Pages are cached for a day in
~/.cache/legal-review (BW Boek 6 alone is 2.4 MB).
"""

import hashlib
import html
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = "legal-review-skill/1.0 (citation check)"
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "legal-review")
TTL = 24 * 3600

# Dutch laws by BWB id. `cite.py nl <BWBR...>` works for anything not listed here.
NL = {
    "BW1": ("BWBR0002656", "Burgerlijk Wetboek Boek 1"),
    "BW2": ("BWBR0003045", "Burgerlijk Wetboek Boek 2"),
    "BW3": ("BWBR0005291", "Burgerlijk Wetboek Boek 3"),
    "BW4": ("BWBR0002761", "Burgerlijk Wetboek Boek 4"),
    "BW5": ("BWBR0005288", "Burgerlijk Wetboek Boek 5"),
    "BW6": ("BWBR0005289", "Burgerlijk Wetboek Boek 6"),
    "BW7": ("BWBR0005290", "Burgerlijk Wetboek Boek 7"),
    "BW7A": ("BWBR0006000", "Burgerlijk Wetboek Boek 7A"),
    "BW8": ("BWBR0005034", "Burgerlijk Wetboek Boek 8"),
    "BW10": ("BWBR0030068", "Burgerlijk Wetboek Boek 10"),
    "RV": ("BWBR0001827", "Wetboek van Burgerlijke Rechtsvordering"),
    "AW": ("BWBR0001886", "Auteurswet"),
    "UAVG": ("BWBR0040940", "Uitvoeringswet Algemene verordening gegevensbescherming"),
    "TW": ("BWBR0009950", "Telecommunicatiewet"),
    "FW": ("BWBR0001860", "Faillissementswet"),
    "HNW": ("BWBR0001906", "Handelsnaamwet"),
    "HRW": ("BWBR0021777", "Handelsregisterwet 2007"),
    "MW": ("BWBR0008691", "Mededingingswet"),
    "AWR": ("BWBR0002320", "Algemene wet inzake rijksbelastingen"),
    "WBB": ("BWBR0041459", "Wet bescherming bedrijfsgeheimen"),
    "OBW": ("BWBR0002565", "Overgangswet nieuw Burgerlijk Wetboek"),
}

# EU acts by CELEX number. `cite.py eu <CELEX>` works for anything not listed here.
EU = {
    "GDPR": ("32016R0679", "General Data Protection Regulation (AVG)"),
    "AVG": ("32016R0679", "General Data Protection Regulation (AVG)"),
    "DATA-ACT": ("32023R2854", "Data Act"),
    "AI-ACT": ("32024R1689", "AI Act"),
    "DSA": ("32022R2065", "Digital Services Act"),
    "NIS2": ("32022L2555", "NIS2 Directive"),
    "CRA": ("32024R2847", "Cyber Resilience Act"),
    "EPRIVACY": ("02002L0058-20091219", "ePrivacy Directive (consolidated 2009)"),
    "LATE-PAYMENT": ("32011L0007", "Late Payment Directive"),
    "UCTD": ("31993L0013", "Unfair Contract Terms Directive"),
    "CRD": ("32011L0083", "Consumer Rights Directive"),
    "DCD": ("32019L0770", "Digital Content Directive"),
    "ROME-I": ("32008R0593", "Rome I Regulation"),
    "BRUSSELS-IA": ("32012R1215", "Brussels I bis Regulation"),
    "PLD": ("32024L2853", "Product Liability Directive (2024)"),
    "EAA": ("32019L0882", "European Accessibility Act"),
    "P2B": ("32019R1150", "Platform-to-Business Regulation"),
    "SCC": ("32021D0914", "Standard contractual clauses for transfers (Decision 2021/914)"),
}

LANGS = {"en": "eng", "nl": "nld", "de": "deu", "fr": "fra"}


def die(code, msg):
    print(msg, file=sys.stderr)
    sys.exit(code)


def fetch(url, accept="text/html", lang=None):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1(f"{url}|{accept}|{lang}".encode()).hexdigest()
    path = os.path.join(CACHE, key)
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < TTL:
        with open(path, encoding="utf-8") as f:
            final, _, body = f.read().partition("\n")
            return final, body
    headers = {"User-Agent": UA, "Accept": accept}
    if lang:
        headers["Accept-Language"] = lang
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", errors="replace")
            final = r.geturl()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        die(3, f"HTTP {e.code} from {url}")
    except Exception as e:  # network, TLS, timeout
        die(3, f"could not reach {url}: {e}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(final + "\n" + body)
    return final, body


def text_of(fragment):
    fragment = re.sub(r'<ul role="list".*?</ul>', " ", fragment, flags=re.S)  # action menus
    fragment = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S)
    fragment = re.sub(r"</(p|li|div|h\d|tr)>", "\n", fragment)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    lines = [re.sub(r"\s+", " ", html.unescape(l)).strip() for l in fragment.split("\n")]
    return "\n".join(l for l in lines if l)


def nl(law, article, date=None):
    article = article.strip()
    key = law.upper().replace(" ", "")
    if key == "BW":
        m = re.fullmatch(r"(\d+A?):(\S+)", article, re.I)
        if not m:
            die(3, "BW needs book:article, e.g. `cite.py nl BW 6:233`")
        key, article = "BW" + m.group(1).upper(), m.group(2)
    elif re.fullmatch(r"\d+A?:\S+", article) and key.startswith("BW"):
        article = article.split(":", 1)[1]
    article = re.sub(r"^(art(ikel)?\.?\s*)", "", article, flags=re.I)
    if key.startswith("BWBR"):
        bwb, name = key, key
    elif key in NL:
        bwb, name = NL[key]
    else:
        die(3, f"unknown law alias {law!r}; run `cite.py laws` or pass a BWBR id (search wetten.overheid.nl)")
    # A bare /<date> URL only works for exact version dates; the jci link resolves any date.
    url = f"https://wetten.overheid.nl/jci1.3:c:{bwb}&g={date}&z={date}" if date else f"https://wetten.overheid.nl/{bwb}/"
    final, page = fetch(url)
    if page is None:
        die(3, f"no regulation at {url}")
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    toestand = re.search(r'data-toestand-id="([^"]+)"', page)
    hits = [m for m in re.finditer(r'<div class="artikel" id="([^"]*?Artikel' + re.escape(article) + r')"', page, re.I)]
    if not hits:
        die(2, f"NOT FOUND: artikel {article} in {name} ({url}). Check the number; it may be repealed (vervallen) or renumbered.")
    out = []
    for m in hits:
        start = m.start()
        nxt = re.compile(r'<div class="[a-z_\-]+" id="').search(page, m.end())
        chunk = page[start: nxt.start() if nxt else start + 20000]
        anchor = m.group(1)
        out.append((anchor, text_of(chunk)))
    print(f"SOURCE: wetten.overheid.nl ({bwb})")
    print(f"TITLE: {html.unescape(title.group(1).strip()) if title else name}")
    print(f"VERSION: geldend op {toestand.group(1) if toestand else 'unknown'}")
    for anchor, txt in out:
        print(f"URL: https://wetten.overheid.nl/{bwb}/{toestand.group(1) if toestand else ''}#{anchor}")
        since = re.search(r'data-hashfragmentid="' + re.escape(anchor) + r'"[^>]*?data-iwt-datum="([^"]+)"', page)
        if since:
            print(f"ARTICLE TEXT IN FORCE SINCE: {since.group(1)}  (a recent date means the article changed; check whether the document predates it)")
        if "vervallen" in txt.lower()[:200]:
            print("NOTE: this article appears to be repealed (vervallen)")
        print("TEXT:")
        print(txt)
        print()


def eu(act, article, lang="en"):
    key = act.upper()
    celex, name = EU.get(key, (act, act))
    if not re.fullmatch(r"[0-9]{5}[A-Z]{1,2}[0-9]{4}(\(\d+\))?(-\d{8})?", celex):
        die(3, f"unknown act {act!r}; run `cite.py laws` or pass a CELEX number like 32016R0679")
    article = re.sub(r"^(art(icle|ikel)?\.?\s*)", "", article.strip(), flags=re.I)
    num = re.match(r"\d+[a-z]*", article)
    if not num:
        die(3, f"cannot read article number from {article!r}")
    url = f"http://publications.europa.eu/resource/celex/{celex}"
    final, page = fetch(url, accept="application/xhtml+xml", lang=LANGS.get(lang, lang))
    if page is None:
        die(3, f"no {lang} text for CELEX {celex} at the Publications Office")
    m = re.search(r'<div class="eli-subdivision" id="art_' + re.escape(num.group(0)) + r'"', page)
    if m:  # current Official Journal markup
        nxt = re.compile(r'<div class="eli-subdivision" id="(art|cpt|anx|tis|sct)_').search(page, m.end())
        fin = page.find('class="oj-final"', m.end())
    else:  # older acts: <p class="ti-art">Article 3</p>
        m = None
        for h in re.finditer(r'<p[^>]*class="ti-art"[^>]*>(.*?)</p>', page, re.S):
            label = re.sub(r"\s+", " ", text_of(h.group(1))).strip()
            if re.fullmatch(r"(Article|Artikel|Artikel|Art\.)\s+" + re.escape(num.group(0)), label, re.I):
                m = h
                break
        if not m:
            die(2, f"NOT FOUND: article {num.group(0)} in {name} (CELEX {celex})")
        nxt = re.compile(r'class="ti-art"').search(page, m.end())
        fin = page.find('class="final"', m.end())
    end = min(nxt.start() if nxt else len(page), fin if fin > 0 else len(page))
    title = re.search(r'<p class="(?:oj-)?doc-ti"[^>]*>(.*?)</p>', page, re.S)
    kind = "consolidated text" if celex.startswith("0") else "original OJ text; if the act was amended, pass its consolidated CELEX (0YYYY...-YYYYMMDD) instead"
    print(f"SOURCE: Publications Office of the EU / EUR-Lex (CELEX {celex}, {kind})")
    doc = text_of(title.group(1)) if title else ""
    print(f"TITLE: {doc} ({name})" if doc and name != act and doc != name else f"TITLE: {doc or name}")
    print(f"URL: https://eur-lex.europa.eu/legal-content/{lang.upper()}/TXT/?uri=CELEX:{celex}")
    print("TEXT:")
    print(text_of(page[m.start():end]))


def ecli(ident):
    ident = ident.strip().upper()
    if not re.fullmatch(r"ECLI:[A-Z]{2}:[A-Z0-9]+:\d{4}:[A-Z0-9.]+", ident):
        die(3, f"not an ECLI: {ident}")
    if not ident.startswith("ECLI:NL:"):
        die(3, "only Dutch ECLIs are supported here. For CJEU (ECLI:EU:...) check curia.europa.eu or EUR-Lex with WebFetch/WebSearch.")
    url = f"https://data.rechtspraak.nl/uitspraken/content?id={ident}"
    final, xml = fetch(url, accept="application/xml")
    if xml is None:
        die(2, f"NOT FOUND: {ident} does not exist in rechtspraak.nl open data")

    def tag(t):
        m = re.search(r"<%s\b[^>]*>(.*?)</%s>" % (t, t), xml, re.S)
        return text_of(m.group(1)) if m else ""

    print("SOURCE: rechtspraak.nl open data")
    print(f"ECLI: {ident}")
    print(f"COURT: {tag('dcterms:creator')}")
    print(f"DATE: {tag('dcterms:date')}")
    print(f"CASE NUMBER: {tag('psi:zaaknummer')}")
    print(f"AREA: {tag('dcterms:subject')}  PROCEDURE: {tag('psi:procedure')}")
    print(f"URL: https://uitspraken.rechtspraak.nl/details?id={ident}")
    summary = tag("inhoudsindicatie")
    print("SUMMARY (inhoudsindicatie):")
    print(summary or "(none published)")


def cjeu(case, lang="en"):
    m = re.fullmatch(r"([CT])-(\d{1,4})/(\d{2})", case.strip().upper().replace("\u2011", "-"))
    if not m:
        die(3, f"not a CJEU case number: {case!r} (expected e.g. C-131/12)")
    court, num, yy = m.groups()
    year = (1900 if int(yy) > 50 else 2000) + int(yy)
    celex = f"6{year}{'CJ' if court == 'C' else 'TJ'}{int(num):04d}"
    _, page = fetch(f"http://publications.europa.eu/resource/celex/{celex}", accept="application/xhtml+xml", lang=LANGS.get(lang, lang))
    if page is None:
        die(2, f"NOT FOUND: no judgment for {case} (CELEX {celex}). It may be an order or an opinion only, or not yet published.")
    head = re.sub(r"\s+", " ", text_of(page))[:1800]
    print("SOURCE: Publications Office of the EU / EUR-Lex (judgment text)")
    print(f"CASE: {case}  CELEX: {celex}")
    print(f"URL: https://curia.europa.eu/juris/liste.jsf?num={court}-{num}/{yy}&language={lang}")
    print("HEADER (court, date, keywords, parties):")
    print(head)


def find(query):
    import urllib.parse
    cql = 'overheidbwb.titel any "%s"' % query.replace('"', "")
    url = ("https://zoekservice.overheid.nl/sru/Search?operation=searchRetrieve&version=1.2"
           "&x-connection=BWB&maximumRecords=15&query=" + urllib.parse.quote(cql))
    _, xml = fetch(url, accept="application/xml")
    recs = re.findall(r"<dcterms:identifier>(BWBR\d+)</dcterms:identifier>\s*<dcterms:title>(.*?)</dcterms:title>\s*<dcterms:type>(.*?)</dcterms:type>", xml or "")
    if not recs:
        die(2, f"no Dutch regulation with {query!r} in its title")
    for bwb, title, kind in dict.fromkeys(recs):
        print(f"{bwb}  {kind:<22} {html.unescape(title)}")


def batch(lines):
    """Check many citations in one call: one `nl|eu|ecli ...` command per line."""
    import shlex
    import subprocess
    counts = {0: 0, 2: 0, 3: 0}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        r = subprocess.run([sys.executable, os.path.abspath(__file__)] + shlex.split(line), capture_output=True, text=True)
        status = {0: "FOUND", 2: "NOT FOUND"}.get(r.returncode, "ERROR")
        counts[r.returncode if r.returncode in counts else 3] += 1
        print(f"=== {line}  [{status}]")
        print((r.stdout + r.stderr).strip())
        print()
    print(f"=== summary: {counts[0]} found, {counts[2]} not found, {counts[3]} errors")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = argv[1]
    opts = {}
    args = []
    it = iter(argv[2:])
    for a in it:
        if a.startswith("--"):
            opts[a[2:]] = next(it, None)
        else:
            args.append(a)
    if cmd == "laws":
        print("Dutch (cite.py nl <alias> <article>):")
        for k, (b, n) in NL.items():
            print(f"  {k:<7} {b}  {n}")
        print("  BW      use book:article, e.g. BW 6:233")
        print("EU (cite.py eu <alias> <article>):")
        for k, (c, n) in EU.items():
            print(f"  {k:<13} {c}  {n}")
    elif cmd == "batch":
        batch(open(args[0]) if args else sys.stdin)
    elif cmd == "cjeu" and len(args) == 1:
        cjeu(args[0], opts.get("lang") or "en")
    elif cmd == "find" and args:
        find(" ".join(args))
    elif cmd == "nl" and len(args) == 2:
        nl(args[0], args[1], opts.get("date"))
    elif cmd == "eu" and len(args) == 2:
        eu(args[0], args[1], opts.get("lang") or "en")
    elif cmd == "ecli" and len(args) == 1:
        ecli(args[0])
    else:
        print(__doc__)
        sys.exit(3)


if __name__ == "__main__":
    main(sys.argv)
