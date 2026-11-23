"""The 12 Cohort 2 Engines from their letter of intent to the award: what stayed and what changed.

For each Engine, across the stages of the second NSF Engines competition (py/00_competition_lists.py):
  lead organisation   LOI, invited preliminary proposal, full proposal, award (data/processed/engines.csv)
  states              LOI vs preliminary proposal (the LOI gives state codes)
  PI                  last name at LOI, preliminary, full proposal, and the current PI of the award
                      (data/processed/people_nsf.csv; NSF marks replaced people "former")
  keywords            Jaccard index of the keyword lists, LOI vs preliminary, preliminary vs full
  coalition           members at the preliminary and full stage, and the share of the preliminary members
                      still named in the full proposal (exact names after case and spaces: a lower bound)

Input:  data/manual/nsf_engines_c2_{proposals,lois,coalitions}.csv, data/processed/{engines,people_nsf}.csv
Output: data/processed/funnel_engines_change.csv
Run:    python3 py/00b_funnel_engines.py        (pandas only)
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MAN, PROC = ROOT / "data" / "manual", ROOT / "data" / "processed"
p = pd.read_csv(MAN / "nsf_engines_c2_proposals.csv")
loi = pd.read_csv(MAN / "nsf_engines_c2_lois.csv")
co = pd.read_csv(MAN / "nsf_engines_c2_coalitions.csv")
eng = pd.read_csv(PROC / "engines.csv")
people = pd.read_csv(PROC / "people_nsf.csv")

STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
          "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
          "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
          "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
          "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
          "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
          "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
          "PR": "Puerto Rico", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
          "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
          "WI": "Wisconsin", "WY": "Wyoming"}
norm = lambda s: re.sub(r"[^a-z]", "", str(s).lower())
name = lambda s: re.sub(r"\s+", " ", str(s).strip().lower())
last = lambda s: str(s).split()[-1].lower() if isinstance(s, str) else ""
kw = lambda s: {name(k) for k in str(s).split(",") if k.strip()} if isinstance(s, str) else set()
jac = lambda a, b: round(len(a & b) / len(a | b), 2) if a | b else None

rows = []
for _, r in p[p.stage == "engine"].iterrows():
    l = loi[loi.loi_id == r.loi_id].iloc[0]
    e = eng[eng.engine_name == r.engine_name].iloc[0]
    pis = people[(people.engine_name == r.engine_name) & (people.role_nsf == "PI")]
    pi_award = pis[~pis.former].name.iloc[0] if (~pis.former).any() else pis.name.iloc[0]
    leads = [l.lead_org, r.lead_org_preliminary, r.lead_org_full, e.lead_org]
    pi_seq = [last(l.pi_last_names), last(r.pi_preliminary), last(r.pi_full), last(pi_award)]
    st_loi = {STATES.get(x.strip(), x.strip()) for x in str(l.states).split(",")}
    st_pre = {x.strip() for x in str(r.states).split(",")}
    cp = set(co[(co.team_id == r.team_id) & (co.stage == "preliminary")].member.map(name))
    cf = set(co[(co.team_id == r.team_id) & (co.stage == "full")].member.map(name))
    rows.append({"engine_name": r.engine_name,
                 "lead_org_same": len({norm(x) for x in leads}) == 1,
                 "lead_org_loi": l.lead_org, "lead_org_award": e.lead_org,
                 "states_same": st_loi == st_pre, "states_loi": "; ".join(sorted(st_loi)),
                 "states_preliminary": "; ".join(sorted(st_pre)),
                 "pi_same": len(set(pi_seq)) == 1, "pi_loi": pi_seq[0], "pi_preliminary": pi_seq[1],
                 "pi_full": pi_seq[2], "pi_award_now": pi_seq[3],
                 "keywords_loi_vs_preliminary": jac(kw(l.keywords), kw(r.keywords_preliminary)),
                 "keywords_preliminary_vs_full": jac(kw(r.keywords_preliminary), kw(r.keywords_full)),
                 "coalition_preliminary": len(cp), "coalition_full": len(cf),
                 "coalition_kept": round(len(cp & cf) / len(cp), 2) if cp else None})
out = pd.DataFrame(rows)
out.to_csv(PROC / "funnel_engines_change.csv", index=False)
print(out[["engine_name", "lead_org_same", "states_same", "pi_same", "coalition_preliminary", "coalition_full",
           "coalition_kept"]].to_string(index=False))
