"""Second NSF Engines competition (Cohort 2): every team from the preliminary proposal to the award, as one table.

Three files published by NSF (downloaded by hand; not kept in the repository because they list the PIs' email):
  1. Nov2024_NSF_Engines_Preliminary_Proposal_Data_0.xlsx       71 preliminary proposals (Nov 2024) + coalitions
  2. data_fullproposals_semifinalists_public_07082.xlsx          29 semifinalists: full proposals (Jul 2025) + coalitions
  3. Download - Proposal Details.csv (UTF-16, tab-separated)      15 finalists (Sep 2025): keywords, key technology areas
  4. Data_Table.csv (UTF-16, tab-separated; optional)             294 letters of intent (LOI): lead organisation and its
                                                                  type, states, keywords, NAICS sectors, PI last names
                                                                  (a crosstab: one column per last name)
Awarded Engines: data/processed/engines.csv (12, Cohort 2), matched by lead organisation.

Sources (NSF published these data to help teams find partners):
  - LOI data, July 2024: https://new.nsf.gov/funding/initiatives/regional-innovation-engines/updates/nsf-publishes-data-letters-intent-submitted-rie
  - the 71 teams invited to full proposals and their coalitions, Nov 2024:
    https://www.nsf.gov/tip/updates/explore-data-collaborate-71-nsf-regional-innovation-engines
    (Tableau: https://tableau.external.nsf.gov/views/NSFEnginesFullProposalInvitations/MapOverview)
  - 29 semifinalists, Jul 2025: https://www.nsf.gov/tip/updates/nsf-advances-29-semifinalists-second-nsf-regional-innovation
  - 15 finalists, Sep 2025: https://www.nsf.gov/news/nsf-selects-15-finalists-advance-next-round-its-second
Checks against NSF's own counts (Nov 2024 page): coalition members of the 71 preliminary proposals, 1,644
distinct names here vs "more than 1,600"; teams led by non-academic organisations, 20 here by the LOI's
organisation type (one team has no LOI) vs NSF's 23 (NSF may count university research foundations and
corporations, which the LOIs type as academic, as non-academic).

Stages are linked by lead organisation, or, where it changed, by at least 3 shared words of the proposal title
(one case: Seafood, University of New Hampshire -> NERACOOS). LOIs are linked to the preliminary proposals the
same way; where neither works, MANUAL_LOI holds a link decided by hand (marked link = "manual"). The PI email
column is dropped.

Output: data/manual/nsf_engines_c2_proposals.csv    one row per team (71): lead organisation and title at each
                                                    stage, states, PI, keywords, furthest stage, engine_name
        data/manual/nsf_engines_c2_coalitions.csv   coalition members by team and stage (preliminary, full)
        data/manual/nsf_engines_c2_lois.csv         one row per LOI (294), team_id if it went on to a preliminary
                                                    proposal, and how it was linked
Run:    python3 py/00_competition_lists.py <preliminary.xlsx> <semifinalists.xlsx> <finalists.csv> [<loi.csv>]
        (pandas, openpyxl)
"""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
pre = pd.read_excel(sys.argv[1], sheet_name=0)
pre_c = pd.read_excel(sys.argv[1], sheet_name=1)
semi = pd.read_excel(sys.argv[2], sheet_name=0)
semi_c = pd.read_excel(sys.argv[2], sheet_name=1)
fin = pd.read_csv(sys.argv[3], sep="\t", encoding="utf-16")
fin.columns = [c.strip() for c in fin.columns]
fin = fin.dropna(subset=["Lead Organization"])
for c in (pre_c, semi_c):
    c[["Lead Organization", "Proposal Title"]] = c[["Lead Organization", "Proposal Title"]].ffill()

norm = lambda s: re.sub(r"[^a-z]", "", str(s).lower())
STOP = {"engine", "engines", "regional", "innovation", "advancing", "technologies", "technology", "through"}
words = lambda s: {w for w in re.findall(r"[a-z]+", str(s).lower()) if len(w) > 3 and w not in STOP}


def link(row, df):
    """Index of the same team in an earlier stage: same lead organisation, else >= 3 shared title words."""
    same = df[df["Lead Organization"].map(norm) == norm(row["Lead Organization"])]
    if len(same):
        return same.index[0]
    best = max(df.index, key=lambda i: len(words(row["Proposal Title"]) & words(df.at[i, "Proposal Title"])))
    return best if len(words(row["Proposal Title"]) & words(df.at[best, "Proposal Title"])) >= 3 else None


semi["pre"] = [link(r, pre) for _, r in semi.iterrows()]
fin["semi"] = [link(r, semi) for _, r in fin.iterrows()]
assert semi.pre.notna().all() and fin.semi.notna().all(), "a team could not be linked to its earlier stage"

# awarded Engines: lead organisation of the NSF award (engines.csv) against the finalists
eng = pd.read_csv(ROOT / "data" / "processed" / "engines.csv")
lead_col = next(c for c in ("lead_org", "lead_organization", "organization") if c in eng.columns)
eng_of = {norm(o): e for o, e in zip(eng[lead_col], eng.engine_name)}

out = pre.drop(columns=["Principal Investigator Email"]).rename(columns={
    "Lead Organization": "lead_org_preliminary", "Proposal Title": "title_preliminary",
    "Performing Place": "place", "Region of Service (State Coverage)": "states",
    "Principal Investigator": "pi_preliminary", "Proposal Keywords": "keywords_preliminary"})
out.insert(0, "team_id", range(1, len(out) + 1))
out["stage"] = "preliminary"
for _, r in semi.iterrows():
    i = r.pre
    out.loc[i, ["lead_org_full", "title_full", "pi_full", "keywords_full", "stage"]] = [
        r["Lead Organization"], r["Proposal Title"], r["Principal Investigator"], r["Proposal Keywords"], "semifinalist"]
for _, r in fin.iterrows():
    i = semi.at[r.semi, "pre"]
    out.loc[i, ["key_technology_areas", "stage"]] = [r.get("Key Technology Areas"), "finalist"]
    e = eng_of.get(norm(r["Lead Organization"]))
    if e:
        out.loc[i, ["stage", "engine_name"]] = ["engine", e]
stage_order = ["loi", "preliminary", "semifinalist", "finalist", "engine"]

# letters of intent (optional 4th file)
MANUAL_LOI = {   # preliminary lead organisation -> LOI ID, decided by hand: same topic and state, other lead org
    "Virginia Commonwealth University": "L02622923",   # RAMP-CV <- "Advanced Pharmaceutical Manufacturing and R&D"
}
if len(sys.argv) > 4:
    t = pd.read_csv(sys.argv[4], encoding="utf-16", sep="\t", header=None, dtype=str)
    names = t.iloc[1, 8:].tolist()
    body = t.iloc[2:].reset_index(drop=True)
    loi = body.iloc[:, :8].copy()
    loi.columns = ["loi_id", "title", "lead_org", "lead_org_type", "lead_org_state", "states", "keywords", "naics"]
    loi["pi_last_names"] = ["; ".join(n for n, v in zip(names, r) if pd.notna(v)) for r in body.iloc[:, 8:].values]
    loi["team_id"], loi["link"] = pd.NA, pd.NA
    for _, r in out.iterrows():
        same = loi[loi.lead_org.map(norm) == norm(r.lead_org_preliminary)]
        if len(same) == 1:
            i, how = same.index[0], "lead organisation"
        else:
            cand = same if len(same) > 1 else loi
            i = max(cand.index, key=lambda j: len(words(r.title_preliminary) & words(loi.at[j, "title"])))
            how = "title" if len(words(r.title_preliminary) & words(loi.at[i, "title"])) >= 3 else None
        if how is None and r.lead_org_preliminary in MANUAL_LOI:
            i, how = loi.index[loi.loi_id == MANUAL_LOI[r.lead_org_preliminary]][0], "manual"
        if how:
            loi.loc[i, ["team_id", "link"]] = [r.team_id, how]
            out.loc[out.team_id == r.team_id, "loi_id"] = loi.at[i, "loi_id"]
    loi.to_csv(ROOT / "data" / "manual" / "nsf_engines_c2_lois.csv", index=False)
    print(f"LOIs: {len(loi)}; went on to a preliminary proposal: {loi.team_id.notna().sum()} "
          f"({loi.link.value_counts().to_dict()}); preliminary proposals without an LOI: {out.loi_id.isna().sum()}")
out["stage"] = pd.Categorical(out.stage, stage_order, ordered=True)

# coalitions, keyed by team_id
team_of_pre = {t: i for i, t in zip(out.team_id, pre["Proposal Title"])}
team_of_semi = {t: out.at[p, "team_id"] for t, p in zip(semi["Proposal Title"], semi.pre)}
co = pd.concat([
    pre_c.assign(stage="preliminary", team_id=pre_c["Proposal Title"].map(team_of_pre)),
    semi_c.assign(stage="full", team_id=semi_c["Proposal Title"].map(team_of_semi))])
co = co.dropna(subset=["Members of the Regional Coalition"]).rename(columns={
    "Members of the Regional Coalition": "member", "Lead Organization": "lead_org", "Proposal Title": "title"})
assert co.team_id.notna().all()
co[["team_id", "stage", "lead_org", "member"]].to_csv(ROOT / "data" / "manual" / "nsf_engines_c2_coalitions.csv",
                                                     index=False)

out.to_csv(ROOT / "data" / "manual" / "nsf_engines_c2_proposals.csv", index=False)
print(out.stage.value_counts().reindex(stage_order).to_string())
print(f"engines matched: {out.engine_name.notna().sum()} of {len(eng)}; coalition rows: "
      f"{(co.stage == 'preliminary').sum()} preliminary, {(co.stage == 'full').sum()} full")
