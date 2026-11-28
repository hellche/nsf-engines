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
