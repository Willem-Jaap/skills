# Official sources

Where to check a citation, per jurisdiction. Only these count as verification. Commentary sites, law firm blogs and AI answers can point you to the right article, but the article itself is read at the official source.

## cite.py

`python3 ~/.agents/skills/legal-review/scripts/cite.py` fetches the official text and prints the title, the version date, a deep link and the text. Exit code 0 means found, 2 not found, 3 unreachable or unknown law. Pages are cached for a day.

| What | Command | Source |
| --- | --- | --- |
| Dutch law | `nl BW 6:233`, `nl BW7 404`, `nl Rv 241`, `nl Aw 45j`, `nl BWBR0001886 2` | wetten.overheid.nl, current version |
| Dutch law on a date | `nl BW 6:96 --date 2024-10-17` | the version in force on that date |
| Find a Dutch law's id | `find Telecommunicatiewet` | zoekservice.overheid.nl (SRU) |
| EU legislation | `eu GDPR 28 --lang nl`, `eu DATA-ACT 13`, `eu 32019L0770 8` | Publications Office (the EUR-Lex text) |
| Amended EU act | `eu 02002L0058-20091219 5` | the consolidated version, by consolidated CELEX |
| Dutch case law | `ecli ECLI:NL:HR:1981:AG4158` | rechtspraak.nl open data: court, date, case number, summary |
| CJEU judgment | `cjeu C-131/12` | Publications Office: court, date, keywords, parties |
| Many at once | `batch citations.txt` (one command per line) | all of the above |
| Aliases | `laws` | |

Known gaps:

- `nl` finds articles by number. Laws numbered with Roman numerals or by chapter (`1.1` in the Telecommunicatiewet) need the number exactly as the law writes it. When it still fails, open the URL it printed and read the article there.
- `eu` reads the Official Journal markup. For an act it cannot parse, use WebFetch on the EUR-Lex page and ask for the article verbatim. EUR-Lex's own site often blocks scripts with a challenge page (HTTP 202 and an empty body); the Publications Office URL that `cite.py` uses does not.
- `ecli` covers Dutch courts only. `cjeu` finds CJEU and General Court judgments by case number, not by ECLI, and not orders or Advocate General opinions.
- The EU text is the original Official Journal text unless you pass a consolidated CELEX. For a regulation or directive that has been amended, check the consolidated version.

## Netherlands

- **Legislation**: wetten.overheid.nl. Deep links look like `https://wetten.overheid.nl/BWBR0005289/2026-07-16#Boek6_Titeldeel5_Afdeling3_Artikel233`; permanent links use `jci1.3:c:BWBR0005289&boek=6&titeldeel=5&afdeling=3&artikel=233`. Directives are implemented in national law, so cite the Dutch article (for example art. 6:119a BW for late payment), and the directive only for interpretation.
- **Case law**: uitspraken.rechtspraak.nl (`/details?id=<ECLI>`), and data.rechtspraak.nl for the machine-readable version. Older judgments that were never published there may only exist in commercial databases; treat them as unverified.
- **Parliamentary history** (kamerstukken, when the meaning of an article turns on it): officielebekendmakingen.nl.
- **Regulators**: Autoriteit Persoonsgegevens (autoriteitpersoonsgegevens.nl) for GDPR guidance, ACM (acm.nl) for consumer law. Guidance is not law; cite it as guidance.
- **Citation style**: art. 6:233 sub a BW; art. 7:408 lid 1 BW; art. 241 Rv; art. 45j Aw; art. 28 lid 3 AVG; HR 13 maart 1981, ECLI:NL:HR:1981:AG4158 (Haviltex).

## European Union

- **Legislation**: EUR-Lex. `cite.py eu` reads the same text through the Publications Office. Language versions are equally authentic, so quote the version in the report language.
- **CJEU case law**: `cite.py cjeu C-131/12` (CELEX `62012CJ0131`), or curia.europa.eu by case number in a browser; curia's search pages return no case data to scripts. Cite by case number and date; add the ECLI (`ECLI:EU:C:<year>:<number>`) only when you have read it on curia or EUR-Lex. Check the date, the parties and the holding before citing.
- **EDPB guidelines** (edpb.europa.eu) for GDPR interpretation: guidance, not law.

## Other jurisdictions

There is no script for these. Use WebFetch or `curl` on the official site, ask for the provision verbatim, and treat a page that will not load as unverified.

- **Belgium**: ejustice.just.fgov.be (Belgisch Staatsblad, consolidated legislation), Justel. Case law: juportal.be.
- **Germany**: gesetze-im-internet.de (for example `https://www.gesetze-im-internet.de/bgb/__307.html`). Case law: rechtsprechung-im-internet.de, bundesgerichtshof.de.
- **United Kingdom**: legislation.gov.uk (England and Wales, Scotland and Northern Ireland differ; ask which). Case law: caselaw.nationalarchives.gov.uk, bailii.org.
- **France**: legifrance.gouv.fr.
- **United States**: there is no single official source; ask the user for the state. Federal law: uscode.house.gov, ecfr.gov. State law: the state legislature's official site.
- **Anything else**: search for the official government legislation portal first (WebSearch with the country name and "official legislation database"), and say in the report which source you used.
