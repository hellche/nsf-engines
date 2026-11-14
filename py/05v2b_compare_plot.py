"""Step 5 v2/v3, part B: compare the v2 and v3 rankings with each other; the v1 choices are marked
for reference only (v1 was an ad hoc manual choice, not a benchmark).

For every Engine: the distribution of the ranking score over ALL OpenAlex topics and ALL CPC main groups,
for v2 (all grant sentences) and v3 (extracted science and technology fragments), with the v1 choices
marked. A v1 code that is a whole subclass (C08L) is marked at its best-scoring main group only.

Input:  data/processed/tech_<v>_rank_oa.csv.gz, tech_<v>_rank_cpc.csv.gz, tech_<v>_run.json (v = v2, v3)
        data/processed/tech_profile.csv (v1)
Output: reports/figures/tech_v2_v3_distributions.png
        data/processed/tech_v2_v3_summary.csv   per Engine x list x version: median rank of v1, share in top-50/200

Run:    .venv/bin/python py/05v2b_compare_plot.py
"""

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = ROOT / "reports" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

v1 = pd.read_csv(PROC / "tech_profile.csv")
rank = {(v, k): pd.read_csv(PROC / f"tech_{v}_rank_{k}.csv.gz") for v in ("v2", "v3") for k in ("oa", "cpc")}
method = {v: json.loads((PROC / f"tech_{v}_run.json").read_text())["method"] for v in ("v2", "v3")}


def v1_rows(r: pd.DataFrame, engine: str, kind: str) -> pd.DataFrame:
    """Rows of ranking r that stand for the Engine's v1 choices (best group for a subclass code)."""
    p = v1[v1.engine_name == engine]
    if kind == "oa":
        return r[r.topic_id.isin(p.topic_id)]
    hits = []
    for codes in p.cpc.dropna():
        for c in [x.strip() for x in codes.split(";") if x.strip()]:
            h = r[r.subclass == c] if len(c) == 4 else r[r.cpc == c + "/00"]
            if len(h):
                hits.append(h.nsmallest(1, "rank"))
    return pd.concat(hits) if hits else r.iloc[0:0]


engines = sorted(rank[("v2", "oa")].engine_name.unique())
cols = [("oa", "v2"), ("oa", "v3"), ("cpc", "v2"), ("cpc", "v3")]
label = {"oa": "OpenAlex topics", "cpc": "CPC main groups"}
fig, axes = plt.subplots(len(engines), 4, figsize=(20, 2.6 * len(engines)))
summary = []
for i, e in enumerate(engines):
    for j, (kind, v) in enumerate(cols):
        r = rank[(v, kind)]
        r = r[r.engine_name == e]
        m = method[v][kind]
        score = r[m].to_numpy()
        hit = v1_rows(r, e, kind)
        summary.append((e, kind, v, m, len(hit), hit["rank"].median(), (hit["rank"] <= 50).mean(),
                        (hit["rank"] <= 200).mean()))
        ax = axes[i, j]
        ax.hist(score, bins=90, color="#b8c2cc", edgecolor="none")
        ax.axvline(np.sort(score)[-50], color="#4a6fa5", ls="--", lw=1)
        ymax = ax.get_ylim()[1]
        ax.vlines(hit[m], 0, ymax * 0.15, color="#c0392b", lw=1.4)
        top = r.nsmallest(3, "rank")
        names = top.topic if kind == "oa" else top.cpc + " " + top.group_title.str.slice(0, 30)
        ax.text(0.99, 0.95, "\n".join(n[:44] for n in names), transform=ax.transAxes, ha="right", va="top",
                fontsize=6.5, color="#333")
        med = hit["rank"].median()
        ax.set_title(f"{e} · {label[kind]} · {v}   (v1 median rank {med:.0f})" if len(hit) else
                     f"{e} · {label[kind]} · {v}", fontsize=8.5, loc="left")
        ax.tick_params(labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        if i == len(engines) - 1:
            ax.set_xlabel(f"score ({m}, centred cosine)", fontsize=8)
fig.suptitle("v2 (all grant sentences) vs v3 (extracted science and technology fragments): every OpenAlex topic and "
             "CPC main group scored for each Engine\ngrey: all items · red: v1 choices (best group for a subclass) · "
             "dashed: top-50 cut-off · corner: top-3", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.985])
fig.savefig(OUT / "tech_v2_v3_distributions.png", dpi=100)

s = pd.DataFrame(summary, columns=["engine_name", "kind", "version", "method", "n_v1", "median_rank_v1",
                                   "share_top50", "share_top200"])
s.to_csv(PROC / "tech_v2_v3_summary.csv", index=False)
print(s.groupby(["kind", "version"])[["median_rank_v1", "share_top50", "share_top200"]].median().round(2))
print(s.pivot_table(index="engine_name", columns=["kind", "version"], values="median_rank_v1").round(0))
