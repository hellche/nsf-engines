"""Profile v3.1, simple version (v3_1s): for each technology of the grant, the 20 OpenAlex topics and the
20 CPC main groups closest in meaning.

  1. Technologies: the 43 common technologies of the grants (data/processed/tech_minplus_technologies.csv,
     the same input as profile v1). Each technology is ONE text: its label and its phrases of the grant
     ("Digital twins and AI decision support. digital twins and AI-enabled decision-support systems; ...").
     The label gives a one-phrase technology some context. The Engine's name and the word "Engine(s)" are
     removed (PatentSBERTa reads "engine" as a motor).
  2. Lists: all 4,516 OpenAlex topics (name + description + keywords) and the 7,646 CPC main groups
     (subclass + group + first-level subgroup titles; indexing groups 2000+ and catch-alls 99/00 left out),
     built exactly as in py/05v2a_embed_rank.py (same texts, same embedding cache file).
  3. Embeddings: SPECTER2 for topics (technologies with the adhoc_query adapter, topics with proximity),
     PatentSBERTa for CPC. Each set is mean-centred and renormalised.
  4. Score = cosine between the technology's vector and the item's vector; every item gets a rank.

  Compared with the complex version (05v2a v3_1 + 05v3_1b): no max / centroid / mix, no rank fusion, no
  subtraction of the other Engines. Step 3 (selection) is not part of this script.

Input:  data/processed/tech_minplus_technologies.csv, data/processed/engines.csv, data/reference/
Output: data/processed/tech_v3_1s_rank_{oa,cpc}.csv.gz   top TOP_KEEP per technology: score and rank
        data/processed/tech_v3_1s_run.json                models, counts, date
        data/raw/tech_items_embeddings_fix.npz            cache shared with 05v2a (not tracked)
Run:    .venv/bin/python py/05v3_1s_simple.py
"""

import hashlib
import json
import re
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent
PROC, RAW, REF = ROOT / "data" / "processed", ROOT / "data" / "raw", ROOT / "data" / "reference"
SPECTER_BASE, SPECTER_DOC, SPECTER_QUERY = "allenai/specter2_base", "allenai/specter2", "allenai/specter2_adhoc_query"
PATENT_MODEL = "AI-Growth-Lab/PatentSBERTa"
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
TOP, TOP_KEEP = 20, 100     # candidates per technology; rows kept in the output (for looking further down)


# ---- technologies: one text each ----------------------------------------------------------------

def engine_name_tokens(e) -> list[str]:
    """As in 05v2a: the Engine's acronym-like name, its acronym, an acronym in brackets after its name."""
    tokens = set()
    first = e.engine_name.split()[0]
    if " " not in e.engine_name and re.search(r"[A-Z].*[A-Z]", e.engine_name):
        tokens.add(e.engine_name)
    elif re.search(r"[a-z][A-Z]|^[A-Z]{3,}$", first):
        tokens.add(first)
    if isinstance(e.acronym, str):
        tokens.add(e.acronym)
    for m in re.finditer(r"([^.;]{0,90})\(([A-Z][A-Za-z-]{1,14})\)", e.abstract):
        if e.engine_name.lower() in m.group(1).lower():
            tokens.add(m.group(2))
    return sorted(tokens, key=len, reverse=True)


def mask(text: str, tokens: list[str]) -> str:
    """As in 05v2a (v3.1 fixes): remove the name and the word Engine(s); nothing is inserted."""
    for t in tokens:
        text = re.sub(rf"(?<![\w-]){re.escape(t)}(?![\w-])", "", text)
    text = re.sub(r"\b[Ee]ngines?\b", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


engines = pd.read_csv(PROC / "engines.csv")
tokens = {e.engine_name: engine_name_tokens(e) for e in engines.itertuples()}
ph = pd.read_csv(PROC / "tech_minplus_technologies.csv")
tech = (ph.groupby(["engine_name", "tech_id", "tech_label"], sort=True)
          .fragment.agg(lambda x: "; ".join(x)).reset_index(name="phrases"))
tech["text"] = [mask(f"{l}. {p}", tokens[e]) for e, l, p in zip(tech.engine_name, tech.tech_label, tech.phrases)]
print(f"Technologies: {len(tech)} ({len(ph)} phrases) in {tech.engine_name.nunique()} Engines")


# ---- lists: exactly as in 05v2a with the v3.1 fixes (same texts -> same cache) -------------------

topics = pd.read_csv(REF / "openalex_topics.csv", keep_default_na=False)
topics["text"] = topics.topic + ". " + topics.description + " Keywords: " + topics.keywords


def clean_cpc(title: str) -> str:
    title = title.replace("{", "").replace("}", "")
    title = re.sub(r"\s*\([^()]*\b[A-HY]\d\d[A-Z]?\d*\b[^()]*\)", "", title)
    return re.sub(r"\s+", " ", title).strip()


ref_cpc = pd.read_csv(REF / "cpc_titles_202608.csv.gz", dtype=str, keep_default_na=False)
subclass_title = {c: clean_cpc(t).capitalize()
                  for c, t in zip(ref_cpc.code, ref_cpc.title) if re.fullmatch(r"[A-HY]\d\d[A-Z]", c)}
main = ref_cpc[ref_cpc.kind == "main_group"]
num = lambda c: int(re.match(r"[A-HY]\d\d[A-Z](\d+)/", c).group(1))
groups = [(c, c[:4], clean_cpc(t)) for c, t in zip(main.code, main.title) if num(c) < 2000 and num(c) != 99]
sub1 = ref_cpc[(ref_cpc.kind == "subgroup") & (ref_cpc.dots == "1")]
sub1_titles = (sub1.assign(main=sub1.code.str.replace(r"/.*$", "/00", regex=True), t=[clean_cpc(t) for t in sub1.title])
               .groupby("main").t.agg(lambda x: "; ".join(x)))
cpc = pd.DataFrame(groups, columns=["cpc", "subclass", "group_title"])
cpc["subclass_title"] = cpc.subclass.map(subclass_title)
cpc["text"] = cpc.subclass_title.fillna("") + ": " + cpc.group_title
cpc["text"] = cpc.text + [f". {sub1_titles[c]}" if c in sub1_titles.index else "" for c in cpc.cpc]
print(f"OpenAlex topics: {len(topics)}; CPC main groups: {len(cpc)}")


# ---- embeddings -----------------------------------------------------------------------------------

def unit(x):
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def centre(x):
    return unit(x - x.mean(axis=0))


def cache_key(*parts) -> str:       # same as 05v2a, so the item cache is shared
    return hashlib.sha256("\x1e".join([SPECTER_BASE, SPECTER_DOC, SPECTER_QUERY, PATENT_MODEL, *parts])
                          .encode()).hexdigest()


from adapters import AutoAdapterModel                 # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402
from transformers import AutoTokenizer                  # noqa: E402

_m = {}


def models():
    if not _m:
        tok = AutoTokenizer.from_pretrained(SPECTER_BASE)
        sp = AutoAdapterModel.from_pretrained(SPECTER_BASE)
        sp.load_adapter(SPECTER_DOC, source="hf", load_as="proximity", set_active=False)
        sp.load_adapter(SPECTER_QUERY, source="hf", load_as="adhoc_query", set_active=False)
        _m.update(tok=tok, specter=sp.to(DEVICE).eval(), patent=SentenceTransformer(PATENT_MODEL, device=DEVICE))
    return _m


def specter_embed(texts, adapter, batch=32):
    m = models(); m["specter"].set_active_adapters(adapter); out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            enc = m["tok"](texts[i:i + batch], padding=True, truncation=True, max_length=512,
                           return_tensors="pt").to(DEVICE)
            out.append(m["specter"](**enc).last_hidden_state[:, 0, :].float().cpu().numpy())
    return unit(np.vstack(out))


items_cache, items_key = RAW / "tech_items_embeddings_fix.npz", cache_key(*topics.text, *cpc.text)
z = np.load(items_cache) if items_cache.exists() else None
if z is not None and "key" in z.files and str(z["key"]) == items_key:
    emb_topics, emb_cpc = z["topics"], z["cpc"]
    print("Topic and CPC embeddings read from cache")
else:
    emb_topics = specter_embed(topics.text.tolist(), "proximity")
    emb_cpc = models()["patent"].encode(cpc.text.tolist(), batch_size=64, normalize_embeddings=True,
                                        show_progress_bar=False)
    np.savez_compressed(items_cache, topics=emb_topics, cpc=emb_cpc, key=np.array(items_key))
    print("Topic and CPC embeddings done (cached)")
tech_sp = specter_embed(tech.text.tolist(), "adhoc_query")
tech_pt = models()["patent"].encode(tech.text.tolist(), batch_size=64, normalize_embeddings=True,
                                    show_progress_bar=False)


# ---- one score: cosine; every item ranked for every technology ------------------------------------

def rank(T, I, items, keep):
    sims = centre(T) @ centre(I).T                       # technologies x items
    out = []
    for k, t in enumerate(tech.itertuples()):
        r = items[keep].copy()
        r.insert(0, "tech_label", t.tech_label); r.insert(0, "tech_id", t.tech_id); r.insert(0, "engine_name", t.engine_name)
        r["score"] = sims[k].round(4)
        r["rank"] = (-sims[k]).argsort().argsort() + 1
        out.append(r.nsmallest(TOP_KEEP, "rank"))
    return pd.concat(out, ignore_index=True)


r_oa = rank(tech_sp, emb_topics, topics, ["topic_id", "topic", "subfield"])
r_cpc = rank(tech_pt, emb_cpc, cpc, ["cpc", "subclass", "group_title"])
r_oa.to_csv(PROC / "tech_v3_1s_rank_oa.csv.gz", index=False)
r_cpc.to_csv(PROC / "tech_v3_1s_rank_cpc.csv.gz", index=False)

import adapters, sentence_transformers, transformers  # noqa: E402,E401
(PROC / "tech_v3_1s_run.json").write_text(json.dumps({
    "version": "v3_1s", "date": date.today().isoformat(), "device": DEVICE,
    "models": {"topics": [SPECTER_BASE, SPECTER_DOC, SPECTER_QUERY], "cpc": PATENT_MODEL},
    "versions": {"torch": torch.__version__, "transformers": transformers.__version__,
                 "adapters": adapters.__version__, "sentence_transformers": sentence_transformers.__version__},
    "counts": {"technologies": len(tech), "phrases": len(ph), "openalex_topics": len(topics), "cpc_main_groups": len(cpc)},
    "score": "cosine, mean-centred, technology text = label + phrases", "top": TOP,
}, indent=2))
print(f"Done: {len(tech)} technologies x {len(topics)} topics and {len(cpc)} CPC groups ranked; "
      f"top {TOP_KEEP} kept per technology")
