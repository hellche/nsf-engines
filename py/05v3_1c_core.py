"""Step 5, version 3.1, part C: the core of the technology profile, chosen by fixed rules (no choice by eye).

For each technology of each Engine and each kind of item (OpenAlex topics, CPC main groups):
  1. if the rank fusion (05v3_1b_fuse.py) has candidates with confirmation "high", the core is the best
     CORE_N of them by fused rank                                          basis = "fusion"
  2. otherwise the judge scores (prompt py/prompts/v3_1_judge.md, data/manual/tech_v3_1_judge_raw.csv) are
     used: candidates with score 3, then 2, best CORE_N by fused rank      basis = "judge (score N)"
  3. otherwise the technology has no core item of that kind               basis = "none" (flagged)
Audit: every item chosen in step 1 was also scored by the judge with the same rubric
(data/manual/tech_v3_1_judge_audit_raw.csv); items with score 0 or 1 are dropped from the core and kept in
the output with in_core = False, so the audit can be seen and undone. Catch-all OpenAlex topics are not
confirmed by the fusion in the first place (05v3_1b_fuse.py).

The judge scores (both files) were made by hand in a Claude Code chat session, not through the API, in one run: they
are NOT reproducible (see the prompt file). Every row records its basis, so the judged rows can be told
apart or dropped.

Input:  data/processed/tech_v3_1_fused_{oa,cpc}.csv.gz, data/manual/tech_v3_1_judge_raw.csv,
        data/manual/tech_v3_1_judge_audit_raw.csv
Output: data/processed/tech_profile_v3_1_core.csv
Run:    .venv/bin/python py/05v3_1c_core.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
CORE_N = 2

judge = pd.read_csv(ROOT / "data" / "manual" / "tech_v3_1_judge_raw.csv")
audit = (pd.read_csv(ROOT / "data" / "manual" / "tech_v3_1_judge_audit_raw.csv")
         .rename(columns={"score": "audit_score", "reason": "audit_reason"}))
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
core = core.merge(audit, how="left", left_on=["kind", "engine_name", "tech_id", "item_id"],
                  right_on=["kind", "engine_name", "tech_id", "item_id"])
core["in_core"] = core.item_id.notna() & ~((core.basis == "fusion") & (core.audit_score <= 1))
missing = core[(core.basis == "fusion") & core.audit_score.isna()]
assert missing.empty, f"fusion items without an audit score: {missing[['engine_name', 'tech_id', 'item_id']].values}"
core.to_csv(PROC / "tech_profile_v3_1_core.csv", index=False)

techs = core.groupby(["engine_name", "tech_id"]).ngroups
print(f"Core: {core.in_core.sum()} items for {techs} technologies "
      f"({((core.basis == 'fusion') & ~core.in_core).sum()} fusion items dropped by the audit)")
empty = core.groupby(["kind", "engine_name", "tech_id"]).in_core.sum()
print(f"Technologies without a core item: topics {(empty['oa'] == 0).sum()}, CPC {(empty['cpc'] == 0).sum()}")
print(core.assign(b=core.basis.str.replace(r" \(score \d\)", "", regex=True))
      .groupby(["kind", "b"]).size().unstack(fill_value=0))
