"""Step 5, version 3.1, part C: the core of the technology profile, chosen by fixed rules (no choice by eye).

For each technology of each Engine and each kind of item (OpenAlex topics, CPC main groups):
  1. if the rank fusion (05v3_1b_fuse.py) has candidates with confirmation "high", the core is the best
     CORE_N of them by fused rank                                          basis = "fusion"
  2. otherwise the judge scores (prompt py/prompts/v3_1_judge.md, data/manual/tech_v3_1_judge_raw.csv) are
     used: candidates with score 3, then 2, best CORE_N by fused rank      basis = "judge (score N)"
  3. otherwise the technology has no core item of that kind               basis = "none" (flagged)

The judge scores were made by hand in a Claude Code chat session, not through the API, in one run: they
are NOT reproducible (see the prompt file). Every row records its basis, so the judged rows can be told
apart or dropped.

Input:  data/processed/tech_v3_1_fused_{oa,cpc}.csv.gz, data/manual/tech_v3_1_judge_raw.csv
Output: data/processed/tech_profile_v3_1_core.csv
Run:    .venv/bin/python py/05v3_1c_core.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
CORE_N = 2

judge = pd.read_csv(ROOT / "data" / "manual" / "tech_v3_1_judge_raw.csv")
rows = []
for kind, idc, title in [("oa", "topic_id", "topic"), ("cpc", "cpc", "group_title")]:
    f = pd.read_csv(PROC / f"tech_v3_1_fused_{kind}.csv.gz")
    j = judge[judge.kind == kind].rename(columns={"item_id": idc})[["engine_name", "tech_id", idc, "score", "reason"]]
    f = f.merge(j, how="left")
    for (e, t), g in f.groupby(["engine_name", "tech_id"]):
        g = g.sort_values("rank_fused")
        high = g[g.confirmation == "high"].head(CORE_N).assign(basis="fusion")
        if len(high):
            pick = high
        else:
            judged = g[g.score >= 2].sort_values(["score", "rank_fused"], ascending=[False, True]).head(CORE_N)
            pick = judged.assign(basis=[f"judge (score {int(s)})" for s in judged.score])
        if len(pick) == 0:
            rows.append({"engine_name": e, "tech_id": t, "tech_label": g.tech_label.iloc[0], "kind": kind,
                         "basis": "none"})
            continue
        for _, r in pick.iterrows():
            rows.append({"engine_name": e, "tech_id": t, "tech_label": r.tech_label, "kind": kind,
                         "item_id": r[idc], "item_title": r[title],
                         "subclass_or_subfield": r.subclass_title if kind == "cpc" else r.subfield,
                         "rank_fused": int(r.rank_fused), "confirmation": r.confirmation, "basis": r.basis,
                         "judge_reason": r.reason if isinstance(r.reason, str) else ""})
core = pd.DataFrame(rows)
core.to_csv(PROC / "tech_profile_v3_1_core.csv", index=False)

techs = core.groupby(["engine_name", "tech_id"]).ngroups
print(f"Core: {core.item_id.notna().sum()} items for {techs} technologies")
print(core.assign(b=core.basis.str.replace(r" \(score \d\)", "", regex=True))
      .groupby(["kind", "b"]).size().unstack(fill_value=0))
