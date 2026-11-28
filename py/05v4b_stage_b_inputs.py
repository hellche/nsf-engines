"""Profile v4, stage B inputs: the candidate groups and topics the judge scores, one file per technology and kind.

Candidates of a technology:
  1. every CPC main group of each subclass, and every OpenAlex topic of each subfield, that stage A kept as
     `part` for it (data/processed/tech_v4_a_consensus.csv);
  2. every item the earlier profiles chose for the matching technology (v1 by levels:
     data/processed/tech_profile_v1_levels.csv; v3.1 simple: data/processed/tech_profile_v3_1s.csv, in_profile),
     so that nothing chosen before is dropped without a score.
Items inside a category kept as `whole` for the same technology are not candidates: they enter the profile anyway.

The earlier profiles use the common technologies (data/processed/tech_minplus_technologies.csv); TECH_MAP says
which v4 technology each of them corresponds to.

Output: <folder>/candidates/t<tech_id>_<kind>.txt (technology header + one candidate per line) and
        data/processed/tech_v4_b_candidates.csv (manifest: Engine, technology, kind, item, title, where it came from).
Needs:  the stage A files in <folder> (py/05v4a_inputs.py <folder>).
Run:    python3 py/05v4b_stage_b_inputs.py <folder>        (pandas only)
Prompt: py/prompts/v4_stage_b_fine.md
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
IN = Path(sys.argv[1])
OUT = IN / "candidates"
OUT.mkdir(parents=True, exist_ok=True)

# common-step technology (tech_minplus_technologies.csv) -> v4 technologies (tech_v4_technologies.csv)
TECH_MAP = {"NEO-SMART": {1: [1], 2: [2], 3: [3, 4], 4: [6]}}


def slug(x: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", x.lower()).strip("_")


def read_items(folder: str, code: str) -> pd.DataFrame:
    rows = [l.rstrip("\n").split("\t") for l in open(IN / folder / f"{code}.txt", encoding="utf-8")
            if not l.startswith("#")]
    return pd.DataFrame([(r[0], r[1], r[2] if len(r) > 2 else "") for r in rows],
                        columns=["item_id", "item_title", "detail"])


topics = pd.read_csv(ROOT / "data" / "reference" / "openalex_topics.csv", keep_default_na=False)
topic_sf = dict(zip(topics.topic_id, topics.subfield.map(slug)))
a = pd.read_csv(PROC / "tech_v4_a_consensus.csv")
tech = pd.read_csv(ROOT / "data" / "manual" / "tech_v4_technologies.csv", dtype={"tech_id": int})

# items of the earlier profiles, mapped to v4 technologies
prior = []
v1 = pd.read_csv(PROC / "tech_profile_v1_levels.csv")
v1 = v1.assign(source="v1 by levels")
v31 = pd.read_csv(PROC / "tech_profile_v3_1s.csv")
v31 = v31[v31.in_profile.astype(str) == "True"].assign(source="v3.1 simple")
for d in (v1, v31):
    for _, r in d.iterrows():
        for t in TECH_MAP.get(r.engine_name, {}).get(int(r.tech_id), []):
            prior.append((r.engine_name, t, r.kind, r.item_id, r.source))
prior = pd.DataFrame(prior, columns=["engine_name", "tech_id", "kind", "item_id", "source"])

man = []
for (e, t), g in a[a.status != "dropped"].groupby(["engine_name", "tech_id"]):
    whole = set(g.loc[g.status == "whole", "code"])
    for kind, folder in (("cpc", "cpc_groups"), ("oa", "oa_topics")):
        cand = []
        for code in g.loc[(g.status == "part") & (g.kind == kind), "code"]:
            cand.append(read_items(folder, code).assign(via=code))
        for _, p in prior[(prior.engine_name == e) & (prior.tech_id == t) & (prior.kind == kind)].iterrows():
            code = p.item_id[:4] if kind == "cpc" else topic_sf[p.item_id]
            if code in whole:
                continue
            x = read_items(folder, code)
            cand.append(x[x.item_id == p.item_id].assign(via=p.source))
        if not cand:
            continue
        c = pd.concat(cand, ignore_index=True)
        c = c.groupby(["item_id", "item_title", "detail"], as_index=False, sort=False).via.agg("; ".join)
        c = c[~c.item_id.str[:4].isin(whole)] if kind == "cpc" else c[~c.item_id.map(topic_sf).isin(whole)]
        tr = tech[(tech.engine_name == e) & (tech.tech_id == t)].iloc[0]
        with open(OUT / f"t{t}_{kind}.txt", "w", encoding="utf-8") as f:
            f.write(f"# engine_name: {e} | tech_id: {t} | label: {tr.tech_label}\n# phrases: {tr.fragments}\n"
                    f"# sentences: {tr.sentences}\n# kind: {kind}\n")
            f.write("# item_id<TAB>title<TAB>" + ("first-level subgroups" if kind == "cpc" else "keywords") +
                    "<TAB>category\n")
            for _, r in c.iterrows():
                cat = r.via.split("; ")[0]
                f.write(f"{r.item_id}\t{r.item_title}\t{r.detail}\t{cat}\n")
        man.append(c.assign(engine_name=e, tech_id=t, kind=kind)[
            ["engine_name", "tech_id", "kind", "item_id", "item_title", "via"]])

man = pd.concat(man, ignore_index=True)
man.to_csv(PROC / "tech_v4_b_candidates.csv", index=False)
print(man.groupby(["engine_name", "tech_id", "kind"]).size().unstack(fill_value=0))
print(f"{len(man)} candidates; from earlier profiles only (outside stage A categories): "
      f"{(~man.via.str.contains(r'^[A-Z]\d\d[A-Z]$|^[a-z_]+$', regex=True) & man.via.str.startswith('v')).sum()}")
