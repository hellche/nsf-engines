"""Step 5, version 3.1, part B: one ranking per technology from several independent signals
(reciprocal rank fusion), instead of a choice by eye.

A single similarity score lets chance matches through: a short fragment such as "digital twins" ranks the
topic "Twin Pregnancy" high. A candidate that several different signals rank high is less likely to be
such an accident. Signals, each a ranking of ALL items for one technology of one Engine:

  OpenAlex topics                                  CPC main groups
  1. max_bg     best fragment of the technology    1. max        best fragment of the technology
  2. centroid_bg  mean of its fragments            2. centroid   mean of its fragments
  3. mix_bg     with the whole Engine as context   3. mix        with the whole Engine as context
  4. OpenAlex's own topic classifier (/text/topics) on the technology's text (label + fragments):
     an independent model trained on works; it returns only a few topics, so it votes only for those.
  (*_bg for topics and plain scores for CPC, as in the Engine-level rankings: METHOD in 05v2a.)

  fused = sum over signals of 1 / (K + rank),  K = 60 (the usual constant of reciprocal rank fusion)

Also reported, not used in the fusion: `votes` = in how many signals the item is in the top VOTE_TOP,
and the item's Engine-level rank in v2_1 (all sentences of the grant: a different input).

Input:  data/raw/tech_v3_1_tech_ranks_all_{oa,cpc}.csv.gz   (05v2a_embed_rank.py v3_1)
        data/processed/tech_v3_1_tech_rank_{oa,cpc}.csv.gz   labels and best fragment
        data/processed/tech_v2_1_rank_{oa,cpc}.csv.gz        Engine-level ranks, v2_1
        data/processed/tech_v3_1_fragments.csv               fragments and technologies
Output: data/processed/tech_v3_1_fused_{oa,cpc}.csv.gz       top FUSED_TOP per technology
        data/raw/openalex_text_topics_v3_1.json              cached classifier responses (not tracked)

Run:    .venv/bin/python py/05v3_1b_fuse.py
        The classifier needs an OpenAlex key: OPENALEX_API_KEY (or ~/.Renviron), or, in a Claude Code cloud
        session, the key saved for api.openalex.org, which the network proxy adds to the request. Without
        one, or if OpenAlex refuses the calls, signal 4 is left out and the run says so.
"""

import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
K = 60
VOTE_TOP = 20
FUSED_TOP = 30
SIGNALS = {"oa": ["max_bg", "centroid_bg", "mix_bg"], "cpc": ["max", "centroid", "mix"]}
ID = {"oa": "topic_id", "cpc": "cpc"}

frag = pd.read_csv(PROC / "tech_v3_1_fragments.csv")
frag = frag[frag.verbatim]
techs = (frag.groupby(["engine_name", "tech_id"])
         .agg(tech_label=("tech_label", "first"), fragments=("fragment", lambda x: "; ".join(x)),
              sentence=("sentence", "first"))
         .reset_index())
techs["classifier_text"] = techs.tech_label + ": " + techs.fragments
# The classifier refuses texts under 20 characters and has little to go on in very short ones
# ("metals: Metals"): those get the grant sentence their first fragment comes from.
short = techs.classifier_text.str.len() < 40
techs.loc[short, "classifier_text"] = techs.classifier_text[short] + ". " + techs.sentence[short]


# ---- OpenAlex classifier (signal 4, topics only) ------------------------------------------------

def openalex_key() -> str:
    key = os.environ.get("OPENALEX_API_KEY", "")
    renviron = Path.home() / ".Renviron"
    if not key and renviron.exists():
        m = re.search(r"^OPENALEX_API_KEY\s*=\s*['\"]?([^'\"\n]+)", renviron.read_text(), re.M)
        key = m.group(1).strip() if m else ""
    return key


cache_path = RAW / "openalex_text_topics_v3_1.json"
cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
key, refused = openalex_key(), None
for text in techs.classifier_text:
    if text in cache or refused:
        continue
    params = {"api_key": key} if key else {}
    for _ in range(30):   # new keys may spend at most $0.10 per 5 minutes ($0.01 per call): wait on 429
        r = requests.post("https://api.openalex.org/text/topics", json={"title": text}, params=params, timeout=60)
        if r.status_code != 429:
            break
        wait = int(r.headers.get("Retry-After") or 60) + 5
        print(f"  OpenAlex 429, waiting {wait} s")
        time.sleep(wait)
    if r.status_code in (401, 403, 429) or r.status_code >= 500:   # no key, no budget, or OpenAlex down
        refused = f"HTTP {r.status_code}: {r.text[:150]}"
        break
    if r.status_code != 200:   # this text refused (e.g. too short): the technology gets no classifier votes
        print(f"  classifier refused '{text[:60]}': HTTP {r.status_code} {r.text[:100]}")
        continue
    cache[text] = [{"topic_id": t["id"].rsplit("/", 1)[-1], "score": t["score"]} for t in r.json()["topics"]]
    cache_path.write_text(json.dumps(cache, indent=1))
n_classified = sum(t in cache for t in techs.classifier_text)
have_classifier = refused is None and n_classified > 0
print(f"OpenAlex classifier: {n_classified} of {len(techs)} technologies classified"
      + (f"; left out of the fusion ({refused})" if refused else ""))


# ---- Fusion -------------------------------------------------------------------------------------

for kind in ("oa", "cpc"):
    idc = ID[kind]
    ranks = pd.read_csv(RAW / f"tech_v3_1_tech_ranks_all_{kind}.csv.gz")
    sig = SIGNALS[kind]
    ranks = ranks[["engine_name", "tech_id", idc] + ["rank_" + s for s in sig]]
    if kind == "oa" and have_classifier:
        cl = pd.DataFrame([(e, t, c["topic_id"], i + 1)
                           for e, t, txt in zip(techs.engine_name, techs.tech_id, techs.classifier_text)
                           for i, c in enumerate(cache.get(txt, []))],
                          columns=["engine_name", "tech_id", idc, "rank_classifier"])
        ranks = ranks.merge(cl, how="left")
        sig = sig + ["classifier"]
    ranks["fused"] = sum((1 / (K + ranks["rank_" + s])).fillna(0) for s in sig)
    ranks["votes"] = sum((ranks["rank_" + s] <= VOTE_TOP).astype(int) for s in sig)
    ranks["rank_fused"] = ranks.groupby(["engine_name", "tech_id"]).fused.rank(ascending=False, method="first").astype(int)
    top = ranks[ranks.rank_fused <= FUSED_TOP]

    # labels, best fragment, the v2_1 Engine-level rank
    labels = (pd.read_csv(PROC / f"tech_v3_1_tech_rank_{kind}.csv.gz")
              .drop(columns=[c for c in pd.read_csv(PROC / f"tech_v3_1_tech_rank_{kind}.csv.gz", nrows=0).columns
                             if c.startswith("rank") or c in ("max", "centroid", "max_bg", "centroid_bg",
                                                              "mix", "mix_bg", "tech_label")]))
    item_cols = {"oa": ["topic_id", "topic", "subfield", "field"],
                 "cpc": ["cpc", "subclass", "subclass_title", "group_title"]}[kind]
    item_info = pd.read_csv(PROC / f"tech_v3_1_rank_{kind}.csv.gz", usecols=item_cols).drop_duplicates(idc)
    v21 = (pd.read_csv(PROC / f"tech_v2_1_rank_{kind}.csv.gz", usecols=["engine_name", idc, "rank"])
           .rename(columns={"rank": "rank_v2_1_engine"}))
    out = (top.merge(techs[["engine_name", "tech_id", "tech_label"]])
           .merge(item_info, on=idc, how="left")
           .merge(labels[["engine_name", "tech_id", idc, "best_frag_id"]].drop_duplicates(), how="left")
           .merge(v21, how="left")
           .sort_values(["engine_name", "tech_id", "rank_fused"]))
    out["fused"] = out.fused.round(5)
    out.to_csv(PROC / f"tech_v3_1_fused_{kind}.csv.gz", index=False)
    print(f"{kind}: signals {sig}; top {FUSED_TOP} of {ranks[idc].nunique()} items for "
          f"{out.groupby(['engine_name', 'tech_id']).ngroups} technologies")
