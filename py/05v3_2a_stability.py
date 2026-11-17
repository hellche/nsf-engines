"""Step 5, common first step (prompt v3.2): the grant's technologies from three independent runs.

Each run of py/prompts/grant_technologies_v3_2.md copies out verbatim fragments of each grant and groups them
into technologies. This script checks every run, measures how much the three runs agree, and builds the
consensus that the profile versions (v1, v3.1) start from.

  1. Checks per run: a fragment must be a verbatim substring of its sentence (a span that differs only in
     hyphen, dash or quote characters is replaced by the exact characters of the sentence); otherwise it is
     dropped. A label must use only words of its technology's fragments (reported, not dropped).
  2. Fragments of different runs are the same when they come from the same sentence and their character
     spans overlap by at least half of the shorter one; such fragments form one "fragment group".
  3. Consensus fragments = groups found in at least 2 of the 3 runs; text = the version most runs used.
  4. Consensus technologies: two consensus fragments are in one technology when at least 2 runs put them
     together; technologies = connected groups. Label = the label of the run technology whose fragments match best
     (Jaccard index of the fragment sets, then the shortest label).
  5. Agreement of the groupings: adjusted Rand index between each pair of runs, over the fragments all three
     runs found (1 = the same grouping, 0 = no better than chance).

Input:  data/manual/tech_v3_2_run{1,2,3}.csv     raw runs (engine_name, sent_id, fragment, tech_id, tech_label)
        data/processed/tech_v2_sentences.csv      the grant sentences (text_original)
Output: data/processed/tech_v3_2_technologies.csv  consensus: Engine x technology x fragment, n_runs
        data/processed/tech_v3_2_stability.csv     per Engine: fragments and technologies per run, consensus, ARI
Run:    python3 py/05v3_2a_stability.py           (pandas only)
"""

import itertools
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MAN, PROC = ROOT / "data" / "manual", ROOT / "data" / "processed"
RUNS = [1, 2, 3]
STOP = {"and", "of", "for", "from", "the", "a", "an", "in", "on", "to", "with", "by"}

sent = pd.read_csv(PROC / "tech_v2_sentences.csv").set_index(["engine_name", "sent_id"]).text_original
norm = str.maketrans({"‑": "-", "‐": "-", "–": "-", "—": "-", "’": "'", "‘": "'",
                      "“": '"', "”": '"'})


def words(t: str) -> set[str]:
    return set(re.findall(r"[a-z0-9/]+", t.translate(norm).lower())) - STOP


# ---- 1. checks per run ---------------------------------------------------------------------------
runs = []
for k in RUNS:
    r = pd.read_csv(MAN / f"tech_v3_2_run{k}.csv", dtype={"fragment": str, "tech_label": str})
    rows, dropped = [], 0
    for _, x in r.iterrows():
        s = sent.get((x.engine_name, int(x.sent_id)))
        if not isinstance(s, str):
            dropped += 1
            continue
        i = s.find(x.fragment)
        if i < 0:
            i = s.translate(norm).find(x.fragment.translate(norm))
        if i < 0:
            dropped += 1
            continue
        rows.append({"run": k, "engine_name": x.engine_name, "sent_id": int(x.sent_id), "start": i,
                     "end": i + len(x.fragment), "fragment": s[i:i + len(x.fragment)],
                     "tech_id": int(x.tech_id), "tech_label": x.tech_label})
    d = pd.DataFrame(rows)
    bad_labels = [(e, t) for (e, t), g in d.groupby(["engine_name", "tech_id"])
                  if words(g.tech_label.iloc[0]) - set().union(*(words(f) for f in g.fragment))]
    print(f"run {k}: {len(d)} verbatim fragments, {dropped} dropped; "
          f"{d.groupby(['engine_name', 'tech_id']).ngroups} technologies; labels with outside words: {len(bad_labels)}")
    runs.append(d)
allf = pd.concat(runs, ignore_index=True)

# ---- 2. fragment groups across runs -------------------------------------------------------------
allf["group"] = -1
gid = 0
for (e, s_id), g in allf.groupby(["engine_name", "sent_id"]):
    idx = list(g.index)
    parent = {i: i for i in idx}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in itertools.combinations(idx, 2):
        ov = min(allf.end[a], allf.end[b]) - max(allf.start[a], allf.start[b])
        if ov >= 0.5 * min(allf.end[a] - allf.start[a], allf.end[b] - allf.start[b]):
            parent[find(a)] = find(b)
    roots = {}
    for i in idx:
        roots.setdefault(find(i), gid + len(roots))
        allf.loc[i, "group"] = roots[find(i)]
    gid += len(roots)

# ---- 3. consensus fragments ---------------------------------------------------------------------
g_runs = allf.groupby("group").run.nunique()
keep = g_runs[g_runs >= 2].index
cons = (allf[allf.group.isin(keep)].groupby("group")
        .agg(engine_name=("engine_name", "first"), sent_id=("sent_id", "first"),
             fragment=("fragment", lambda x: Counter(x).most_common(1)[0][0]),
             start=("start", "min"), n_runs=("run", "nunique"))
        .reset_index())

# ---- 4. consensus technologies ------------------------------------------------------------------
tech_of = {(k, gr): t for k, gr, t in zip(allf.run, allf.group, allf.tech_id)}
out = []
for e, c in cons.groupby("engine_name", sort=False):
    groups = list(c.group)
    parent = {g: g for g in groups}

    def find(g):
        while parent[g] != g:
            parent[g] = parent[parent[g]]
            g = parent[g]
        return g
    for a, b in itertools.combinations(groups, 2):
        together = sum(1 for k in RUNS if (k, a) in tech_of and (k, b) in tech_of and tech_of[(k, a)] == tech_of[(k, b)])
        if together >= 2:
            parent[find(a)] = find(b)
    comps = {}
    for g in sorted(groups, key=lambda g: (c.set_index("group").sent_id[g], c.set_index("group").start[g])):
        comps.setdefault(find(g), []).append(g)
    for t, (root, members) in enumerate(comps.items(), start=1):
        # label: the run technology whose fragments match this one best (Jaccard), then the shortest label
        mset = set(members)
        cand = []
        for (k, t_id), rt in allf[(allf.engine_name == e)].groupby(["run", "tech_id"]):
            rset = set(rt.group)
            if rset & mset:
                cand.append((len(rset & mset) / len(rset | mset), -len(rt.tech_label.iloc[0]), rt.tech_label.iloc[0]))
        label = max(cand)[2]
        for g in members:
            r = c[c.group == g].iloc[0]
            out.append({"engine_name": e, "tech_id": t, "tech_label": label, "sent_id": r.sent_id,
                        "fragment": r.fragment, "n_runs": r.n_runs})
techs = pd.DataFrame(out)
techs.to_csv(PROC / "tech_v3_2_technologies.csv", index=False)


# ---- 5. agreement of the groupings --------------------------------------------------------------
def ari(a: list, b: list) -> float:
    """Adjusted Rand index of two labelings of the same items."""
    from math import comb
    n = len(a)
    if n < 2:
        return float("nan")
    cont = Counter(zip(a, b))
    sa, sb = Counter(a), Counter(b)
    idx = sum(comb(v, 2) for v in cont.values())
    ea, eb = sum(comb(v, 2) for v in sa.values()), sum(comb(v, 2) for v in sb.values())
    exp, mx = ea * eb / comb(n, 2), (ea + eb) / 2
    return 1.0 if mx == exp else (idx - exp) / (mx - exp)


stab = []
for e in sent.index.get_level_values(0).unique():
    f = allf[allf.engine_name == e]
    common = [g for g, n in f.groupby("group").run.nunique().items() if n == 3]
    aris = [ari([tech_of[(a, g)] for g in common], [tech_of[(b, g)] for g in common])
            for a, b in itertools.combinations(RUNS, 2)]
    row = {"engine_name": e}
    for k in RUNS:
        fk = f[f.run == k]
        row[f"fragments_run{k}"] = len(fk)
        row[f"technologies_run{k}"] = fk.tech_id.nunique()
    t = techs[techs.engine_name == e]
    row.update({"fragment_groups": f.group.nunique(), "in_all_3": len(common),
                "consensus_fragments": len(t), "consensus_technologies": t.tech_id.nunique(),
                "ari_mean": round(sum(aris) / len(aris), 3) if common else float("nan"),
                "ari_min": round(min(aris), 3) if common else float("nan")})
    stab.append(row)
stab = pd.DataFrame(stab)
stab.to_csv(PROC / "tech_v3_2_stability.csv", index=False)

g_n = allf.groupby("group").run.nunique()
print(f"fragment groups: {len(g_n)}; in 3 runs {int((g_n == 3).sum())}, in 2 {int((g_n == 2).sum())}, "
      f"in 1 {int((g_n == 1).sum())}")
print(f"consensus: {len(techs)} fragments, {techs.groupby(['engine_name', 'tech_id']).ngroups} technologies; "
      f"mean ARI {stab.ari_mean.mean():.2f}")
print(stab[["engine_name", "technologies_run1", "technologies_run2", "technologies_run3",
            "consensus_technologies", "in_all_3", "ari_mean"]].to_string(index=False))
