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
  4. Agreement of the groupings: adjusted Rand index between each pair of runs, over the fragments all three
     runs found (1 = the same grouping, 0 = no better than chance). Consensus technologies = the grouping of
     the medoid run of each Engine (the run with the highest mean agreement with the other two), on the
     consensus fragments; a consensus fragment the medoid run lacks joins the medoid technology that holds most
     of its companions in the other runs. Labels are the medoid run's. So the consensus is the real grouping
     of one run, not a patchwork of three.

Input:  data/manual/tech_v3_2_run{1,2,3}.csv     raw runs (engine_name, sent_id, fragment, tech_id, tech_label)
        data/processed/tech_v2_sentences.csv      the grant sentences (text_original)
Output: data/processed/tech_v3_2_technologies.csv  consensus: Engine x technology x fragment, n_runs
        data/processed/tech_v3_2_stability.csv     per Engine: fragments and technologies per run, consensus, ARI
Run:    python3 py/05v3_2a_stability.py [tag]     (pandas only; tag = v3_2 by default, or min for the
        minimal prompt py/prompts/grant_technologies_minimal.md: files tech_<tag>_run{1,2,3}.csv and so on)
"""

import itertools
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MAN, PROC = ROOT / "data" / "manual", ROOT / "data" / "processed"
RUNS = [1, 2, 3]
TAG = sys.argv[1] if len(sys.argv) > 1 else "v3_2"
STOP = {"and", "of", "for", "from", "the", "a", "an", "in", "on", "to", "with", "by"}

sent = pd.read_csv(PROC / "tech_v2_sentences.csv").set_index(["engine_name", "sent_id"]).text_original
norm = str.maketrans({"‑": "-", "‐": "-", "–": "-", "—": "-", "’": "'", "‘": "'",
                      "“": '"', "”": '"'})


def words(t: str) -> set[str]:
    return set(re.findall(r"[a-z0-9/]+", t.translate(norm).lower())) - STOP


# ---- 1. checks per run ---------------------------------------------------------------------------
runs = []
for k in RUNS:
    r = pd.read_csv(MAN / f"tech_{TAG}_run{k}.csv", dtype={"fragment": str, "tech_label": str})
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

# ---- 4. agreement of the groupings, and the consensus technologies -----------------------------
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



tech_of = {(k, gr): t for k, gr, t in zip(allf.run, allf.group, allf.tech_id)}
label_of = {(k, t, e): l for k, t, e, l in zip(allf.run, allf.tech_id, allf.engine_name, allf.tech_label)}
out, ari_tab, medoid_of = [], {}, {}
for e in sent.index.get_level_values(0).unique():
    f = allf[allf.engine_name == e]
    common = [g for g, n in f.groupby("group").run.nunique().items() if n == 3]
    pair = {(x, y): ari([tech_of[(x, g)] for g in common], [tech_of[(y, g)] for g in common])
            for x, y in itertools.combinations(RUNS, 2)}
    ari_tab[e] = pair
    # medoid run: the highest mean agreement with the other two (ties: more consensus fragments, then run order)
    c_e = cons[cons.engine_name == e]
    score = {k: (sum(v for (x, y), v in pair.items() if k in (x, y)) / 2,
                 sum((k, g) in tech_of for g in c_e.group), -k) for k in RUNS}
    med = max(score, key=score.get)
    medoid_of[e] = med
    # consensus fragments keep the medoid's technology; a fragment the medoid run lacks goes to the medoid
    # technology that holds most of its companions in the other runs (a new technology if none)
    assign = {}
    for g in c_e.group:
        if (med, g) in tech_of:
            assign[g] = tech_of[(med, g)]
    extra_id = 1000
    for g in c_e.group:
        if g in assign:
            continue
        votes = Counter()
        for k in RUNS:
            if (k, g) in tech_of:
                mates = [h for h in c_e.group if h != g and (k, h) in tech_of and tech_of[(k, h)] == tech_of[(k, g)]]
                votes.update(assign[h] for h in mates if h in assign)
        if votes:
            assign[g] = votes.most_common(1)[0][0]
        else:
            assign[g] = extra_id
            extra_id += 1
    # renumber technologies 1, 2, ... in order of first appearance
    order = sorted(c_e.itertuples(), key=lambda r: (r.sent_id, r.start))
    ren = {}
    for r in order:
        ren.setdefault(assign[r.group], len(ren) + 1)
    for r in order:
        t_old = assign[r.group]
        if t_old < 1000:
            label = label_of[(med, t_old, e)]
        else:
            k0 = next(k for k in RUNS if (k, r.group) in tech_of)
            label = label_of[(k0, tech_of[(k0, r.group)], e)]
        out.append({"engine_name": e, "tech_id": ren[t_old], "tech_label": label, "sent_id": r.sent_id,
                    "fragment": r.fragment, "n_runs": r.n_runs, "medoid_run": med})
techs = pd.DataFrame(out)
techs.to_csv(PROC / f"tech_{TAG}_technologies.csv", index=False)


stab = []
for e in sent.index.get_level_values(0).unique():
    f = allf[allf.engine_name == e]
    common = [g for g, n in f.groupby("group").run.nunique().items() if n == 3]
    aris = list(ari_tab[e].values())
    row = {"engine_name": e}
    for k in RUNS:
        fk = f[f.run == k]
        row[f"fragments_run{k}"] = len(fk)
        row[f"technologies_run{k}"] = fk.tech_id.nunique()
    t = techs[techs.engine_name == e]
    row.update({"fragment_groups": f.group.nunique(), "in_all_3": len(common),
                "consensus_fragments": len(t), "consensus_technologies": t.tech_id.nunique(),
                "medoid_run": medoid_of[e],
                "ari_mean": round(sum(aris) / len(aris), 3) if common else float("nan"),
                "ari_min": round(min(aris), 3) if common else float("nan")})
    stab.append(row)
stab = pd.DataFrame(stab)
stab.to_csv(PROC / f"tech_{TAG}_stability.csv", index=False)

g_n = allf.groupby("group").run.nunique()
print(f"fragment groups: {len(g_n)}; in 3 runs {int((g_n == 3).sum())}, in 2 {int((g_n == 2).sum())}, "
      f"in 1 {int((g_n == 1).sum())}")
print(f"consensus: {len(techs)} fragments, {techs.groupby(['engine_name', 'tech_id']).ngroups} technologies; "
      f"mean ARI {stab.ari_mean.mean():.2f}")
print(stab[["engine_name", "technologies_run1", "technologies_run2", "technologies_run3",
            "consensus_technologies", "in_all_3", "ari_mean"]].to_string(index=False))
