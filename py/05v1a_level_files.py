"""Profile v1 (by levels), part A: the files a language model reads to choose topics and CPC groups level by level.

  technologies.txt              the 43 common technologies (label + phrases of the grant)
  cpc_subclasses.txt            652 CPC subclasses that have main groups (scheme 2026.08)
  cpc_groups/<subclass>.txt     main groups of each subclass with the titles of their first-level subgroups;
                                indexing groups (2000+) and catch-all groups (99/00) left out, as in v3.1
  oa_subfields.txt              250 OpenAlex subfields (domain > field > subfield) and their file names
  oa_topics/<subfield>.txt      OpenAlex topics of each subfield with keywords

Input:  data/reference/cpc_titles_202608.csv.gz, data/reference/openalex_topics.csv,
        data/processed/tech_minplus_technologies.csv
Run:    python3 py/05v1a_level_files.py <output folder>       (pandas only)
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1])
(OUT / "cpc_groups").mkdir(parents=True, exist_ok=True)
(OUT / "oa_topics").mkdir(parents=True, exist_ok=True)


def clean(t: str) -> str:
    """Drop {curly} markers and parenthetical references to other CPC places."""
    t = t.replace("{", "").replace("}", "")
    t = re.sub(r"\s*\([^()]*\b[A-HY]\d\d[A-Z]?\d*\b[^()]*\)", "", t)
    return re.sub(r"\s+", " ", t).strip()


def slug(x: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", x.lower()).strip("_")


# CPC
c = pd.read_csv(ROOT / "data" / "reference" / "cpc_titles_202608.csv.gz", dtype=str, keep_default_na=False)
sub = c[c.kind == "subclass"].set_index("code").title
main = c[c.kind == "main_group"].copy()
num = main.code.str.extract(r"^[A-HY]\d\d[A-Z](\d+)/")[0].astype(int)
main = main[(num < 2000) & (num != 99)]
s1 = c[(c.kind == "subgroup") & (c.dots == "1")].assign(main=lambda d: d.code.str.replace(r"/.*$", "/00", regex=True))
s1t = s1.groupby("main").title.agg(lambda x: "; ".join(clean(t) for t in x))
main["sc"] = main.code.str[:4]
lines = []
for sc, g in main.groupby("sc"):
    title = clean(sub.get(sc, "")).capitalize()
    lines.append(f"{sc}\t{title}")
    with open(OUT / "cpc_groups" / f"{sc}.txt", "w", encoding="utf-8") as f:
        f.write(f"# Main groups of CPC subclass {sc}: {title}\n# code<TAB>title<TAB>first-level subgroups\n")
        for code, t in zip(g.code, g.title):
            f.write(f"{code}\t{clean(t)}\t{s1t.get(code, '')}\n")
(OUT / "cpc_subclasses.txt").write_text("# CPC subclasses (scheme 2026.08) with at least one main group\n"
                                        "# code<TAB>title\n" + "\n".join(lines) + "\n", encoding="utf-8")

# OpenAlex
t = pd.read_csv(ROOT / "data" / "reference" / "openalex_topics.csv", keep_default_na=False)
sf = t.groupby(["domain", "field", "subfield"]).size().reset_index(name="n")
with open(OUT / "oa_subfields.txt", "w", encoding="utf-8") as f:
    f.write("# OpenAlex subfields: file name<TAB>domain > field > subfield<TAB>number of topics\n")
    for _, r in sf.iterrows():
        f.write(f"{slug(r.subfield)}\t{r.domain} > {r.field} > {r.subfield}\t{r.n}\n")
for s, g in t.groupby("subfield"):
    with open(OUT / "oa_topics" / f"{slug(s)}.txt", "w", encoding="utf-8") as f:
        f.write(f"# OpenAlex topics in subfield {s}\n# topic_id<TAB>topic<TAB>keywords\n")
        for _, r in g.iterrows():
            f.write(f"{r.topic_id}\t{r.topic}\t{r.keywords}\n")

# technologies
tech = pd.read_csv(ROOT / "data" / "processed" / "tech_minplus_technologies.csv")
with open(OUT / "technologies.txt", "w", encoding="utf-8") as f:
    for (e, k), g in tech.groupby(["engine_name", "tech_id"], sort=False):
        f.write(f"engine_name: {e} | tech_id: {k} | label: {g.tech_label.iloc[0]}\n  phrases: "
                + " | ".join(g.fragment) + "\n")
print(f"{len(lines)} subclasses, {len(main)} groups, {len(sf)} subfields, {len(t)} topics, "
      f"{tech.groupby(['engine_name', 'tech_id']).ngroups} technologies -> {OUT}")
