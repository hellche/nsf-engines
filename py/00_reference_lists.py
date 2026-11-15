"""Download the two public classification lists used by the technology profile (step 5, v2/v3/v3.1)
and keep them in the repository as CSV, so that the profile can be rebuilt without local files.

  CPC titles     Cooperative Patent Classification, title list of the August 2026 scheme
                 https://www.cooperativepatentclassification.org/cpcSchemeAndDefinitions/bulk
                 file: https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCTitleList202608.zip
                 -> data/reference/cpc_titles_202608.csv.gz
                    every code: section, class, subclass, main group (C22B3/00) and subgroup,
                    with `dots` = subgroup depth (1 = first level under the main group) and the official title
  OpenAlex topics  all topics of the OpenAlex topic classification, with description and keywords
                 https://api.openalex.org/topics   (docs: https://docs.openalex.org/api-entities/topics)
                 -> data/reference/openalex_topics.csv
                    topic_id, topic, description, keywords, subfield, field, domain

Run:  python3 py/00_reference_lists.py           (standard library only)
      OPENALEX_API_KEY is used if set; without it OpenAlex allows a small budget per 5 minutes,
      and the script waits when it is used up (the whole list is ~23 pages).
"""

import csv
import gzip
import io
import json
import os
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "reference"
OUT.mkdir(parents=True, exist_ok=True)

CPC_URL = "https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCTitleList202608.zip"
TOPICS_URL = "https://api.openalex.org/topics"


def get(url: str) -> bytes:
    """GET with waiting on HTTP 429 (OpenAlex budget per 5 minutes)."""
    for _ in range(20):
        try:
            # the CPC site refuses the default "Python-urllib" user agent
            req = urllib.request.Request(url, headers={"User-Agent": "nsf-engines-reference-lists"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = int(e.headers.get("Retry-After") or 60) + 5
            print(f"  429 from {urllib.parse.urlsplit(url).netloc}, waiting {wait} s")
            time.sleep(wait)
    raise RuntimeError(f"gave up on {url}")


# ---- CPC titles ----------------------------------------------------------------------------------

def cpc_kind(code: str) -> str:
    if len(code) == 1:
        return "section"
    if len(code) == 3:
        return "class"
    if len(code) == 4:
        return "subclass"
    return "main_group" if code.endswith("/00") else "subgroup"


rows = []
with zipfile.ZipFile(io.BytesIO(get(CPC_URL))) as z:
    for name in sorted(n for n in z.namelist() if n.endswith(".txt")):
        for line in z.read(name).decode("utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            code, dots, title = parts[0], parts[1], parts[2]
            rows.append((code, cpc_kind(code), dots, title))
with gzip.open(OUT / "cpc_titles_202608.csv.gz", "wt", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["code", "kind", "dots", "title"])
    w.writerows(rows)
n_main = sum(r[1] == "main_group" for r in rows)
print(f"CPC: {len(rows)} codes, {n_main} main groups")


# ---- OpenAlex topics -----------------------------------------------------------------------------

key = os.environ.get("OPENALEX_API_KEY", "")
topics, page = [], 1
while True:   # page numbers, not a cursor: ~4,500 topics fit in the 10,000-result page limit
    params = {"per-page": 200, "page": page,
              "select": "id,display_name,description,keywords,subfield,field,domain"}
    if key:
        params["api_key"] = key
    res = json.loads(get(TOPICS_URL + "?" + urllib.parse.urlencode(params)))["results"]
    if not res:
        break
    topics += res
    page += 1

name = lambda x: (x or {}).get("display_name", "")
with open(OUT / "openalex_topics.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["topic_id", "topic", "description", "keywords", "subfield", "field", "domain"])
    for t in sorted(topics, key=lambda t: int(t["id"].rsplit("/T", 1)[-1])):
        kw = "; ".join(k["display_name"] if isinstance(k, dict) else k for k in t.get("keywords") or [])
        w.writerow([t["id"].rsplit("/", 1)[-1], t["display_name"], t.get("description") or "", kw,
                    name(t.get("subfield")), name(t.get("field")), name(t.get("domain"))])
print(f"OpenAlex topics: {len(topics)}")

(OUT / "README.md").write_text(f"""# Reference lists

Downloaded by `py/00_reference_lists.py` on {date.today().isoformat()}.

| File | Source | Rows |
|---|---|---|
| `cpc_titles_202608.csv.gz` | CPC title list, scheme 2026.08: {CPC_URL} (bulk page: https://www.cooperativepatentclassification.org/cpcSchemeAndDefinitions/bulk) | {len(rows)} codes, {n_main} main groups |
| `openalex_topics.csv` | OpenAlex topics API: {TOPICS_URL} (docs: https://docs.openalex.org/api-entities/topics) | {len(topics)} topics |

Versions: the CPC site labels the title list "CPC Title List (2026.08)" (files dated 2026-08-01).
OpenAlex gives its topic list no version number; `created_date` of the topics in the API is January 2024;
`updated_date` changes daily with the work counts.

`dots` in the CPC file is the depth of a subgroup under its main group (empty for sections, classes
and subclasses, 0 for main groups). Titles are as published, including {{curly}} markers and references.
""", encoding="utf-8")
