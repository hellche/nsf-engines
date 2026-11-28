"""Profile v4: consensus of the three judge runs.

Stage A (coarse):  data/manual/tech_v4_a_run{1,2,3}.csv -> data/processed/tech_v4_a_consensus.csv
  one row per Engine x technology x category marked by any run: n_marked (runs that marked it), n_whole,
  status = whole (all 3 runs say whole) | part (>= 2 runs mark it, not all 3 say whole) | dropped (1 run),
  the three marks and reasons side by side.
Stage B (fine), once its runs exist: data/manual/tech_v4_b_run{1,2,3}.csv -> data/processed/tech_profile_v4.csv
  (written by the stage B part below).

Run:  python3 py/05v4c_consensus.py        (pandas only)
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MAN, PROC = ROOT / "data" / "manual", ROOT / "data" / "processed"
KEY = ["engine_name", "tech_id", "kind", "code"]

runs = []
for i in (1, 2, 3):
    f = MAN / f"tech_v4_a_run{i}.csv"
    if not f.exists():
        raise SystemExit(f"missing {f}")
    d = pd.read_csv(f, dtype=str).drop_duplicates(KEY)
    d["mark"] = d["mark"].str.strip().str.lower()
    runs.append(d.assign(run=i))
a = pd.concat(runs, ignore_index=True)
bad = a[~a["mark"].isin(["whole", "part"])]
if len(bad):
    raise SystemExit(f"unknown marks:\n{bad}")

wide = a.pivot_table(index=KEY, columns="run", values=["mark", "reason"], aggfunc="first")
wide.columns = [f"{v}{r}" for v, r in wide.columns]
wide = wide.reset_index()
title = a.groupby(KEY)["title"].first().reset_index()
cons = title.merge(wide, on=KEY)
marks = cons[[f"mark{i}" for i in (1, 2, 3)]]
cons["n_marked"] = marks.notna().sum(axis=1)
cons["n_whole"] = (marks == "whole").sum(axis=1)
cons["status"] = "dropped"
cons.loc[cons.n_marked >= 2, "status"] = "part"
cons.loc[cons.n_whole == 3, "status"] = "whole"   # stricter than ">= 2": decided 2026-11-28
cons["tech_id"] = cons.tech_id.astype(int)
cons = cons.sort_values(["engine_name", "tech_id", "kind", "status", "code"],
                        key=lambda s: s.map({"whole": 0, "part": 1, "dropped": 2}) if s.name == "status" else s)
cols = KEY + ["title", "status", "n_marked", "n_whole"] + [f"mark{i}" for i in (1, 2, 3)] + \
       [f"reason{i}" for i in (1, 2, 3)]
cons[cols].to_csv(PROC / "tech_v4_a_consensus.csv", index=False)

print(cons.groupby(["engine_name", "tech_id", "kind", "status"]).size().unstack(fill_value=0))
kept = cons[cons.status != "dropped"]
agree = (cons.n_marked == 3).sum() / len(cons)
print(f"\ncategories marked by any run: {len(cons)}, kept: {len(kept)}, marked by all 3 runs: {agree:.0%}")

# ---- stage B ------------------------------------------------------------------------------------------------
# Runs are split in parts by technology (data/manual/tech_v4_b_run<r>_part<p>.csv); a run = all its parts.
# Profile v4 (data/processed/tech_profile_v4.csv), one row per Engine x technology x item:
#   level  subclass (CPC subclass kept `whole` in stage A: every group in it counts),
#          topic    (OpenAlex topic: of a subfield kept `whole`, or scored in stage B),
#          group    (CPC main group scored in stage B)
#   basis  "stage A: whole (3 of 3 runs)" or "stage B: score >= 2 in k of 3 runs"
# data/processed/tech_v4_b_scores.csv keeps every candidate with its three scores, kept or not.
bfiles = sorted(MAN.glob("tech_v4_b_run*_part*.csv"))
runs_b = sorted({int(f.name.split("_run")[1].split("_")[0]) for f in bfiles})
if runs_b != [1, 2, 3]:
    raise SystemExit(f"stage B: runs found {runs_b}, need 1-3; profile not written")
cand = pd.read_csv(PROC / "tech_v4_b_candidates.csv", dtype={"tech_id": int})
BK = ["engine_name", "tech_id", "kind", "item_id"]
sc = cand[BK + ["item_title", "via"]].copy()
for r in (1, 2, 3):
    d = pd.concat([pd.read_csv(f, dtype={"tech_id": int}) for f in bfiles if f"_run{r}_" in f.name])
    d = d.drop_duplicates(BK)
    miss = len(sc.merge(d[BK], on=BK, how="left", indicator=True).query("_merge == 'left_only'"))
    if miss:
        raise SystemExit(f"stage B run {r}: {miss} candidates without a score")
    sc = sc.merge(d[BK + ["score", "reason"]].rename(columns={"score": f"score{r}", "reason": f"reason{r}"}),
                  on=BK, how="left")
s3 = sc[[f"score{r}" for r in (1, 2, 3)]]
sc["n_ge2"] = (s3 >= 2).sum(axis=1)
sc["mean_score"] = s3.mean(axis=1).round(2)
sc["in_profile"] = sc.n_ge2 >= 2
sc.to_csv(PROC / "tech_v4_b_scores.csv", index=False)

tech = pd.read_csv(MAN / "tech_v4_technologies.csv", dtype={"tech_id": int})[["engine_name", "tech_id", "tech_label"]]
topics = pd.read_csv(ROOT / "data" / "reference" / "openalex_topics.csv", keep_default_na=False)
topics["sf"] = topics.subfield.str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_")
whole = cons[cons.status == "whole"]
prof = [whole[whole.kind == "cpc"].assign(item_id=lambda d: d.code, item_title=lambda d: d.title,
                                          level="subclass", basis="stage A: whole (3 of 3 runs)")]
wo = whole[whole.kind == "oa"].merge(topics[["topic_id", "topic", "sf"]], left_on="code", right_on="sf")
prof.append(wo.assign(item_id=wo.topic_id, item_title=wo.topic, level="topic",
                      basis="stage A: whole subfield " + wo.code + " (3 of 3 runs)"))
kept = sc[sc.in_profile]
prof.append(kept.assign(level=kept.kind.map({"cpc": "group", "oa": "topic"}),
                        basis="stage B: score >= 2 in " + kept.n_ge2.astype(str) + " of 3 runs"))
prof = pd.concat(prof, ignore_index=True).merge(tech, on=["engine_name", "tech_id"])
cols = ["engine_name", "tech_id", "tech_label", "kind", "level", "item_id", "item_title", "basis", "mean_score",
        "score1", "score2", "score3", "reason1"]
prof = prof[cols].sort_values(["engine_name", "tech_id", "kind", "level", "item_id"])
prof.to_csv(PROC / "tech_profile_v4.csv", index=False)
agree_b = (s3.nunique(axis=1) == 1).mean()
print(f"\nstage B: {len(sc)} candidates, {sc.in_profile.sum()} kept; identical score in all 3 runs: {agree_b:.0%}")
print(prof.groupby(["engine_name", "tech_id", "tech_label", "kind", "level"]).size().unstack(fill_value=0))
