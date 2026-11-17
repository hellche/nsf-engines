"""Profile v1 (by levels), part B: check the three runs of prompt v1_select_by_levels.md and build the profile.

  1. Checks per run: every item must exist in the files the model read (a CPC main group kept in
     cpc_groups/, or an OpenAlex topic id); invalid items are dropped and counted. At most 2 items per
     technology and kind are kept (the first 2 the run gave).
  2. Votes: for each technology and kind, the number of runs that chose each item.
  3. Profile = items chosen by at least 2 of the 3 runs; if more than 2 qualify, the 2 with most votes
     (ties: the order of the first run that chose them).
  4. Agreement: share of chosen items that the other runs also chose, and the same at the level of the
     CPC subclass (C22B) and the OpenAlex subfield.

The runs were made by separate model sessions in a chat environment, not through the API: not reproducible
as such (the prompt and the input files are).

Input:  data/manual/tech_v1_run{1,2,3}.csv, data/processed/tech_minplus_technologies.csv,
        data/reference/ (to check the codes)
Output: data/processed/tech_profile_v1_levels.csv   Engine x technology x item, votes
Run:    python3 py/05v1b_levels_consensus.py           (pandas only)
"""

import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUNS = [1, 2, 3]

c = pd.read_csv(ROOT / "data" / "reference" / "cpc_titles_202608.csv.gz", dtype=str, keep_default_na=False)
main = c[c.kind == "main_group"].code
num = main.str.extract(r"^[A-HY]\d\d[A-Z](\d+)/")[0].astype(int)
valid_cpc = set(main[(num < 2000) & (num != 99)])
topics = pd.read_csv(ROOT / "data" / "reference" / "openalex_topics.csv", keep_default_na=False)
valid_oa = set(topics.topic_id)
subfield_of = dict(zip(topics.topic_id, topics.subfield))
title_of = {**dict(zip(topics.topic_id, topics.topic)),
            **dict(zip(c.code, c.title))}
tech = pd.read_csv(ROOT / "data" / "processed" / "tech_minplus_technologies.csv")
labels = tech.groupby(["engine_name", "tech_id"]).tech_label.first()

runs = []
for k in RUNS:
    r = pd.read_csv(ROOT / "data" / "manual" / f"tech_v1_run{k}.csv", dtype=str, keep_default_na=False)
    r["tech_id"] = r.tech_id.astype(int)
    r["item_id"] = r.item_id.str.strip()
    r["kind"] = r.kind.str.strip().str.lower()
    ok = [(i in valid_cpc) if kd == "cpc" else (i in valid_oa) for i, kd in zip(r.item_id, r.kind)]
    bad = r[[not x for x in ok]]
    r = r[ok].drop_duplicates(["engine_name", "tech_id", "kind", "item_id"])
    r["pos"] = r.groupby(["engine_name", "tech_id", "kind"]).cumcount()
    r = r[r.pos < 2].assign(run=k)
    missing = set(labels.index) - set(zip(r.engine_name, r.tech_id))
    print(f"run {k}: {len(r)} items ({(r.kind == 'oa').sum()} topics, {(r.kind == 'cpc').sum()} CPC); "
          f"invalid {len(bad)}{': ' + ', '.join(bad.item_id[:6]) if len(bad) else ''}; technologies without items {len(missing)}")
    runs.append(r)
allr = pd.concat(runs, ignore_index=True)

votes = (allr.groupby(["engine_name", "tech_id", "kind", "item_id"])
         .agg(votes=("run", "nunique"), first_run=("run", "min"), first_pos=("pos", "min")).reset_index())
prof = (votes[votes.votes >= 2]
        .sort_values(["engine_name", "tech_id", "kind", "votes", "first_run", "first_pos"],
                     ascending=[True, True, True, False, True, True]))
prof = prof.groupby(["engine_name", "tech_id", "kind"]).head(2).copy()
prof["tech_label"] = [labels[(e, t)] for e, t in zip(prof.engine_name, prof.tech_id)]
prof["item_title"] = prof.item_id.map(title_of)
prof["level1"] = [i[:4] if k == "cpc" else subfield_of[i] for i, k in zip(prof.item_id, prof.kind)]
prof = prof[["engine_name", "tech_id", "tech_label", "kind", "item_id", "item_title", "level1", "votes"]]
prof.to_csv(ROOT / "data" / "processed" / "tech_profile_v1_levels.csv", index=False)

# agreement
allr["level1"] = [i[:4] if k == "cpc" else subfield_of[i] for i, k in zip(allr.item_id, allr.kind)]
for kind in ("oa", "cpc"):
    d = allr[allr.kind == kind]
    for col, name in (("item_id", "item"), ("level1", "subclass" if kind == "cpc" else "subfield")):
        shared = []
        for (e, t), g in d.groupby(["engine_name", "tech_id"]):
            sets = {k: set(g[g.run == k][col]) for k in RUNS}
            for k in RUNS:
                others = set().union(*(sets[j] for j in RUNS if j != k))
                shared += [x in others for x in sets[k]]
        print(f"{kind}: share of chosen {name}s also chosen by another run: {sum(shared) / len(shared):.0%}")
n = prof.groupby(["engine_name", "tech_id", "kind"]).size().unstack(fill_value=0).reindex(labels.index, fill_value=0)
print(f"profile: {len(prof)} items; technologies without a topic {int((n['oa'] == 0).sum())}, "
      f"without a CPC group {int((n['cpc'] == 0).sum())} (of {len(labels)})")
