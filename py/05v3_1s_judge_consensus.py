"""Profile v3.1 (simple), step 3: from three judge runs to the profile.

  1. Checks per run: every scored item must be one of the technology's 50 candidates of that kind
     (tech_v3_1s_rank_*.csv.gz, rank <= 50) and the score must be 0-3; anything else is dropped and counted;
     candidates a run did not score are counted as missing.
  2. An item is "about the technology" in a run when its score is 2 or 3 (rubric: 3 directly about it,
     2 clearly part of it).
  3. Profile = items that at least 2 of the 3 runs find about the technology; at most 2 per technology and
     kind: the highest mean score first, then the closest by embedding (rank).
  4. Agreement: exact score agreement of each pair of runs, and the share of candidates where all three runs
     agree on "about the technology" (yes or no).

The runs were made by separate model sessions in a chat (subagents), each run split in two halves by Engine,
not through the API: not reproducible as such (the prompt py/prompts/v3_1s_judge.md and the candidate lists
are).

Input:  data/manual/tech_v3_1s_judge_run{1,2,3}.csv, data/processed/tech_v3_1s_rank_{oa,cpc}.csv.gz
Output: data/processed/tech_profile_v3_1s.csv   every candidate with its three scores; in_profile marks the profile
Run:    .venv/bin/python py/05v3_1s_judge_consensus.py
"""

from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC, MAN = ROOT / "data" / "processed", ROOT / "data" / "manual"
RUNS, TOP, PER_TECH = [1, 2, 3], 50, 2

cand = []
for kind, key, title in (("oa", "topic_id", "topic"), ("cpc", "cpc", "group_title")):
    r = pd.read_csv(PROC / f"tech_v3_1s_rank_{kind}.csv.gz")
    r = r[r["rank"] <= TOP]
    cand.append(pd.DataFrame({"kind": kind, "engine_name": r.engine_name, "tech_id": r.tech_id,
                              "tech_label": r.tech_label, "item_id": r[key].astype(str), "item_title": r[title],
                              "rank_embedding": r["rank"]}))
cand = pd.concat(cand, ignore_index=True)
keys = ["kind", "engine_name", "tech_id", "item_id"]

for k in RUNS:
    s = pd.read_csv(MAN / f"tech_v3_1s_judge_run{k}.csv", dtype={"item_id": str})
    s["score"] = pd.to_numeric(s.score, errors="coerce")
    valid = s.merge(cand[keys], on=keys, how="inner")
    valid = valid[valid.score.between(0, 3)].drop_duplicates(keys)
    print(f"run {k}: {len(s)} rows, valid {len(valid)}, dropped {len(s) - len(valid)}, "
          f"missing {len(cand) - len(valid)} of {len(cand)} candidates")
    cand = cand.merge(valid[keys + ["score"]].rename(columns={"score": f"score{k}"}), on=keys, how="left")

sc = [f"score{k}" for k in RUNS]
cand["n_about"] = (cand[sc] >= 2).sum(axis=1)
cand["mean_score"] = cand[sc].mean(axis=1).round(2)
cand = cand.sort_values(["kind", "engine_name", "tech_id", "mean_score", "rank_embedding"],
                        ascending=[True, True, True, False, True])
ok = cand.n_about >= 2
cand["in_profile"] = False
cand.loc[ok, "in_profile"] = cand[ok].groupby(["kind", "engine_name", "tech_id"]).cumcount() < PER_TECH
cand.to_csv(PROC / "tech_profile_v3_1s.csv", index=False)

for a, b in combinations(sc, 2):
    both = cand[[a, b]].dropna()
    print(f"exact agreement {a} vs {b}: {(both[a] == both[b]).mean():.0%}")
yes = cand[sc].dropna()
print(f"all three agree on 'about the technology' (yes/no): {((yes >= 2).all(axis=1) | (yes < 2).all(axis=1)).mean():.0%}")
prof = cand[cand.in_profile]
n_tech = cand.groupby(["engine_name", "tech_id"]).ngroups
for kind in ("oa", "cpc"):
    have = prof[prof.kind == kind].groupby(["engine_name", "tech_id"]).ngroups
    print(f"{kind}: {int((prof.kind == kind).sum())} items in the profile; technologies without one: {n_tech - have} of {n_tech}")
