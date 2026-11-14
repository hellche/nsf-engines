"""Step 5, version 2, part A: rank ALL OpenAlex topics and ALL CPC main groups for each Engine
by embedding similarity to the sentences of its NSF grant.

Version 1 (R/05_tech_profile.R) stays as it is; this is a separate, formal procedure:
  1. Grant text: the title and every sentence of the NSF abstract, each embedded on its own
     (no manual selection; the NSF boilerplate sentence at the end is dropped). The Engine's own
     name and acronym are replaced by "the Engine", so that a name such as BRIDGES or IMPACT does not
     match CPC groups on bridges or projectiles (rule in engine_name_tokens()).
  2. OpenAlex topics (~4,500): name + description + keywords, embedded with SPECTER2
     (scientific text; documents with the "proximity" adapter, grant sentences with "adhoc_query").
  3. CPC main groups (~9,900, e.g. C22B3/00): subclass title + group title, embedded with PatentSBERTa
     (trained on patents); grant sentences with the same model.
  4. Embeddings are mean-centred (each set by its own mean) and renormalised: raw SPECTER2 cosines all
     sit in a narrow band (~0.61-0.75), which hides the difference between related and unrelated.
  5. Four scores per Engine x item, all kept in the output:
       max        highest cosine over the Engine's sentences (the sentence is kept as evidence)
       centroid   cosine to the mean vector of the Engine's sentences
       *_bg       the same minus its mean over the other 11 Engines (language all grants share cancels out)
     The ranking uses the method set in METHOD below (a working choice). Where the version 1 choices
     rank is printed and saved in tech_<v>_v1_ranks.csv for reference only: v1 was an ad hoc manual
     choice, not a benchmark. Nothing is dropped.
  Part B (LLM) scores the top of these rankings.

Input:  data/processed/engines.csv, data/processed/tech_profile.csv (v1, for the comparison only)
        PATENT_DIR/CPCTitleList202608/cpc-section-*.txt   official CPC titles
        OpenAlex /topics (downloaded once, cached in data/raw/openalex_topics.json)
        v3 only: data/manual/tech_v3_fragments_raw.csv   fragments extracted with py/prompts/v3_extract_technical.md
Output: data/processed/tech_v2_sentences.csv       Engine x sentence (v2 input; v3 checks its fragments against it)
        data/processed/tech_v3_fragments.csv        v3 input: fragments, masked text, verbatim check
        data/processed/tech_<v>_rank_oa.csv.gz      Engine x topic: four scores, ranks, best sentence/fragment
        data/processed/tech_<v>_rank_cpc.csv.gz     Engine x CPC main group: the same
        data/processed/tech_<v>_v1_ranks.csv        where the v1 topics and codes rank
        data/processed/tech_<v>_run.json            models, versions, counts, date

Versions: v2 = every sentence of the title and abstract; v3 = only the science and technology fragments
          extracted from those sentences by the fixed prompt (each fragment must be a verbatim substring
          of its sentence, else it is dropped). Everything after the input is the same.

Run:    .venv/bin/python py/05v2a_embed_rank.py v2      (or v3; Python 3.12; models download once)
"""

import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import torch

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
PATENT_DIR = Path(os.environ.get("PATENT_DIR", "/Users/elenachechik/Desktop/india/patent/data"))
CPC_DIR = PATENT_DIR / "CPCTitleList202608"

SPECTER_BASE = "allenai/specter2_base"
SPECTER_DOC = "allenai/specter2"               # proximity adapter: documents (topics)
SPECTER_QUERY = "allenai/specter2_adhoc_query"  # short queries (grant sentences)
PATENT_MODEL = "AI-Growth-Lab/PatentSBERTa"

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
BOILERPLATE = re.compile(r"This award reflects NSF.s statutory mission", re.I)
METHODS = ["max", "centroid", "max_bg", "centroid_bg"]
METHOD = {"oa": "max_bg", "cpc": "centroid"}   # working choice; the v1 check at the end is a reference, not a benchmark
VERSION = sys.argv[1] if len(sys.argv) > 1 else "v2"
assert VERSION in ("v2", "v3"), "version must be v2 or v3"


# ---- 1. Grant sentences -------------------------------------------------------------------------

def split_sentences(text: str) -> list[str]:
    """Split on . ! ? followed by a space and a capital letter, digit or quote (keeps 'U.S. leadership')."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])", re.sub(r"\s+", " ", text).strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


def engine_name_tokens(e) -> list[str]:
    """Words that only name the Engine: its name when it is one acronym-like word (BRIDGES, NEO-SMART,
    RuralSTAMINA; not 'Seafood', an ordinary word about the technology),
    the acronym in engines.csv (QuantumCT, NSPIRE), and an acronym in brackets right after the Engine's
    name in the abstract ('Critical Materials Crossroads (CMC)'). Technical acronyms such as
    'musculoskeletal (MSK)' do not follow the Engine's name and are kept."""
    tokens = set()
    first = e.engine_name.split()[0]
    if " " not in e.engine_name and re.search(r"[A-Z].*[A-Z]", e.engine_name):   # an acronym, not 'Seafood'
        tokens.add(e.engine_name)
    elif re.search(r"[a-z][A-Z]|^[A-Z]{3,}$", first):   # 'RuralSTAMINA Biomanufacturing' -> RuralSTAMINA
        tokens.add(first)
    if isinstance(e.acronym, str):
        tokens.add(e.acronym)
    for m in re.finditer(r"([^.;]{0,90})\(([A-Z][A-Za-z-]{1,14})\)", e.abstract):
        if e.engine_name.lower() in m.group(1).lower():
            tokens.add(m.group(2))
    return sorted(tokens, key=len, reverse=True)


def mask(text: str, tokens: list[str]) -> str:
    for t in tokens:
        text = re.sub(rf"(?<![\w-]){re.escape(t)}(?![\w-])", "the Engine", text)
    text = re.sub(r"\(the Engine\)", "", text)
    text = re.sub(r"\b(the|The) (NSF )?the Engine", r"\1 Engine", text)
    return re.sub(r"\s+", " ", text).strip()


engines = pd.read_csv(PROC / "engines.csv")
rows, masked_tokens = [], {}
for _, e in engines.iterrows():
    tokens = engine_name_tokens(e)
    masked_tokens[e.engine_name] = tokens
    rows.append((e.engine_name, 0, "title", e.title, mask(e.title, tokens)))
    sents = [s for s in split_sentences(e.abstract) if not BOILERPLATE.search(s)]
    rows += [(e.engine_name, i + 1, "abstract", s, mask(s, tokens)) for i, s in enumerate(sents)]
sentences = pd.DataFrame(rows, columns=["engine_name", "sent_id", "source", "text_original", "text"])
sentences.to_csv(PROC / "tech_v2_sentences.csv", index=False)
print(f"Sentences: {len(sentences)} for {sentences.engine_name.nunique()} Engines; masked: {masked_tokens}")

if VERSION == "v3":
    # Fragments must be verbatim substrings of their sentence: the model may not add words of its own
    frag = pd.read_csv(ROOT / "data" / "manual" / "tech_v3_fragments_raw.csv")
    frag = frag.merge(sentences[["engine_name", "sent_id", "text_original"]].rename(
        columns={"text_original": "sentence"}), on=["engine_name", "sent_id"], how="left")
    frag["verbatim"] = [isinstance(t, str) and f in t for f, t in zip(frag.fragment, frag.sentence)]
    tok = {e: masked_tokens[e] for e in masked_tokens}
    frag["text"] = [mask(f, tok[e]) for f, e in zip(frag.fragment, frag.engine_name)]
    frag.to_csv(PROC / "tech_v3_fragments.csv", index=False)
    if (~frag.verbatim).any():
        print(f"Dropped {int((~frag.verbatim).sum())} fragments that are not verbatim")
    frag = frag[frag.verbatim].reset_index(drop=True)
    frag["frag_id"] = frag.groupby("engine_name").cumcount() + 1
    sentences = pd.DataFrame({"engine_name": frag.engine_name, "sent_id": frag.frag_id,
                              "source": "fragment of sentence " + frag.sent_id.astype(str),
                              "text_original": frag.fragment, "text": frag.text})
    print(f"v3 input: {len(sentences)} verbatim fragments")


# ---- 2. OpenAlex topics (all of them) -----------------------------------------------------------

def openalex_key() -> str:
    """OPENALEX_API_KEY from the environment, else from ~/.Renviron (where the R steps keep it)."""
    key = os.environ.get("OPENALEX_API_KEY", "")
    renviron = Path.home() / ".Renviron"
    if not key and renviron.exists():
        m = re.search(r"^OPENALEX_API_KEY\s*=\s*['\"]?([^'\"\n]+)", renviron.read_text(), re.M)
        key = m.group(1).strip() if m else ""
    return key


topics_cache = RAW / "openalex_topics.json"
if topics_cache.exists():
    topics_raw = json.loads(topics_cache.read_text())
else:
    topics_raw, page, key = [], 1, openalex_key()
    while True:   # page numbers, not a cursor: ~4,500 topics fit in OpenAlex's 10,000-result page limit
        params = {"per-page": 200, "page": page,
                  "select": "id,display_name,description,keywords,subfield,field,domain"}
        if key:
            params["api_key"] = key
        r = requests.get("https://api.openalex.org/topics", timeout=60, params=params)
        r.raise_for_status()
        res = r.json()["results"]
        if not res:
            break
        topics_raw += res
        page += 1
    topics_cache.write_text(json.dumps(topics_raw))
topics = pd.DataFrame({
    "topic_id": [t["id"].rsplit("/", 1)[-1] for t in topics_raw],
    "topic": [t["display_name"] for t in topics_raw],
    "subfield": [t["subfield"]["display_name"] for t in topics_raw],
    "field": [t["field"]["display_name"] for t in topics_raw],
    "text": [f'{t["display_name"]}. {t.get("description") or ""} Keywords: '
             f'{"; ".join(k["display_name"] if isinstance(k, dict) else k for k in t.get("keywords") or [])}'
             for t in topics_raw],
})
print(f"OpenAlex topics: {len(topics)}")


# ---- 3. CPC main groups (all of them) -----------------------------------------------------------

def clean_cpc(title: str) -> str:
    """Drop {curly} markers and parenthetical references to other CPC places, e.g. '(... C10J)'."""
    title = title.replace("{", "").replace("}", "")
    title = re.sub(r"\s*\([^()]*\b[A-HY]\d\d[A-Z]?\d*\b[^()]*\)", "", title)
    return re.sub(r"\s+", " ", title).strip()


subclass_title, groups = {}, []
for f in sorted(CPC_DIR.glob("cpc-section-*.txt")):
    for line in f.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        code, _, title = parts[0], parts[1], parts[2]
        if re.fullmatch(r"[A-HY]\d\d[A-Z]", code):
            subclass_title[code] = clean_cpc(title).capitalize()   # subclass titles are in capitals
        elif re.fullmatch(r"[A-HY]\d\d[A-Z]\d+/00", code):
            groups.append((code, code[:4], clean_cpc(title)))
cpc = pd.DataFrame(groups, columns=["cpc", "subclass", "group_title"])
cpc["subclass_title"] = cpc.subclass.map(subclass_title)
cpc["text"] = cpc.subclass_title.fillna("") + ": " + cpc.group_title
print(f"CPC main groups: {len(cpc)} in {cpc.subclass.nunique()} subclasses")


# ---- 4. Embeddings ------------------------------------------------------------------------------

def unit(x: np.ndarray) -> np.ndarray:
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def specter_embed(texts: list[str], adapter: str, model, tok, batch: int = 32) -> np.ndarray:
    model.set_active_adapters(adapter)
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            enc = tok(texts[i:i + batch], padding=True, truncation=True, max_length=512,
                      return_tensors="pt").to(DEVICE)
            out.append(model(**enc).last_hidden_state[:, 0, :].float().cpu().numpy())  # [CLS]
    return unit(np.vstack(out))


from adapters import AutoAdapterModel                 # noqa: E402  (heavy imports after the data steps)
from sentence_transformers import SentenceTransformer  # noqa: E402
from transformers import AutoTokenizer                  # noqa: E402

# Embeddings are cached in data/raw (not tracked) under a hash of the texts and the models, so any change
# to a text (e.g. the name masking) recomputes them. The topic and CPC embeddings (14k texts, minutes) are
# cached apart from the grant texts, so v2 and v3 share them.
def cache_key(*parts) -> str:
    return hashlib.sha256("\x1e".join([SPECTER_BASE, SPECTER_DOC, SPECTER_QUERY, PATENT_MODEL, *parts])
                          .encode()).hexdigest()


def cached(path: Path, key: str):
    if path.exists():
        z = np.load(path)
        if "key" in z.files and str(z["key"]) == key:
            return z
    return None


_models = {}


def models():
    if not _models:
        tok = AutoTokenizer.from_pretrained(SPECTER_BASE)
        specter = AutoAdapterModel.from_pretrained(SPECTER_BASE)
        specter.load_adapter(SPECTER_DOC, source="hf", load_as="proximity", set_active=False)
        specter.load_adapter(SPECTER_QUERY, source="hf", load_as="adhoc_query", set_active=False)
        _models.update(tok=tok, specter=specter.to(DEVICE).eval(),
                       patent=SentenceTransformer(PATENT_MODEL, device=DEVICE))
    return _models


items_cache = RAW / "tech_items_embeddings.npz"
items_key = cache_key(*topics.text, *cpc.text)
z = cached(items_cache, items_key)
if z is not None:
    emb_topics, emb_cpc = z["topics"], z["cpc"]
    print("Topic and CPC embeddings read from cache")
else:
    m = models()
    emb_topics = specter_embed(topics.text.tolist(), "proximity", m["specter"], m["tok"])
    emb_cpc = m["patent"].encode(cpc.text.tolist(), batch_size=64, normalize_embeddings=True,
                                 show_progress_bar=False)
    np.savez_compressed(items_cache, topics=emb_topics, cpc=emb_cpc, key=np.array(items_key))
    print("Topic and CPC embeddings done")

text_cache = RAW / f"tech_{VERSION}_text_embeddings.npz"
text_key = cache_key(*sentences.text)
z = cached(text_cache, text_key)
if z is not None:
    emb_sent_sp, emb_sent_pt = z["sent_sp"], z["sent_pt"]
    print("Grant text embeddings read from cache")
else:
    m = models()
    emb_sent_sp = specter_embed(sentences.text.tolist(), "adhoc_query", m["specter"], m["tok"])
    emb_sent_pt = m["patent"].encode(sentences.text.tolist(), batch_size=64, normalize_embeddings=True,
                                     show_progress_bar=False)
    np.savez_compressed(text_cache, sent_sp=emb_sent_sp, sent_pt=emb_sent_pt, key=np.array(text_key))
    print("Grant text embeddings done")


# ---- 5. Score and rank every item for every Engine ----------------------------------------------

def centre(x: np.ndarray) -> np.ndarray:
    """Subtract the set's mean vector and renormalise (removes the direction all vectors share)."""
    return unit(x - x.mean(axis=0))


def rank_all(items: pd.DataFrame, emb_items: np.ndarray, emb_sent: np.ndarray, keep: list[str],
             method: str) -> pd.DataFrame:
    """Four scores per Engine x item (see the module docstring); `rank` follows `method`,
    rank_<m> gives the rank under each of the four."""
    I, S = centre(emb_items), centre(emb_sent)
    groups = sentences.groupby("engine_name").groups
    engs = list(groups)
    sc = {"max": [], "centroid": []}
    best = []
    for eng in engs:
        idx = np.asarray(groups[eng])
        sims = S[idx] @ I.T                                          # sentences x items
        sc["max"].append(sims.max(axis=0))
        sc["centroid"].append((unit(S[idx].mean(axis=0, keepdims=True)) @ I.T)[0])
        best.append(sentences.sent_id.to_numpy()[idx][sims.argmax(axis=0)])
    for m in ("max", "centroid"):                                    # Engines x items
        a = np.vstack(sc[m])
        sc[m] = a
        sc[m + "_bg"] = a - (a.sum(axis=0) - a) / (len(engs) - 1)   # minus the mean of the other Engines
    out = []
    for k, eng in enumerate(engs):
        r = items[keep].copy()
        r.insert(0, "engine_name", eng)
        for m in METHODS:
            r[m] = sc[m][k].round(4)
            r["rank_" + m] = (-sc[m][k]).argsort().argsort() + 1
        r["best_sent_id"] = best[k]
        r["rank"] = r["rank_" + method]
        out.append(r.sort_values("rank"))
    return pd.concat(out, ignore_index=True)


rank_oa = rank_all(topics, emb_topics, emb_sent_sp, ["topic_id", "topic", "subfield", "field"], METHOD["oa"])
rank_cpc = rank_all(cpc, emb_cpc, emb_sent_pt, ["cpc", "subclass", "subclass_title", "group_title"], METHOD["cpc"])
rank_oa.to_csv(PROC / f"tech_{VERSION}_rank_oa.csv.gz", index=False)
rank_cpc.to_csv(PROC / f"tech_{VERSION}_rank_cpc.csv.gz", index=False)


# ---- 6. Where do the v1 choices rank in v2, under each method? ----------------------------------

v1 = pd.read_csv(PROC / "tech_profile.csv")
cmp = []
for _, p in v1.iterrows():
    t = rank_oa[(rank_oa.engine_name == p.engine_name) & (rank_oa.topic_id == p.topic_id)]
    cmp.append([p.engine_name, p.item, "openalex_topic", p.topic_id, p.topic, len(topics)]
               + [int(t["rank_" + m].iloc[0]) if len(t) else None for m in METHODS])
    for code in [c.strip() for c in str(p.cpc).split(";") if c.strip() and str(p.cpc) != "nan"]:
        # a v1 code is a subclass (C22B) or a main group (B29B17): best rank among the groups it covers
        hit = rank_cpc[(rank_cpc.engine_name == p.engine_name) &
                       ((rank_cpc.subclass == code) if len(code) == 4 else (rank_cpc.cpc == code + "/00"))]
        cmp.append([p.engine_name, p.item, "cpc", code, subclass_title.get(code[:4], ""), len(cpc)]
                   + [int(hit["rank_" + m].min()) if len(hit) else None for m in METHODS])
cmp = pd.DataFrame(cmp, columns=["engine_name", "item", "kind", "code", "label", "n_ranked"]
                   + ["rank_" + m for m in METHODS])
cmp.to_csv(PROC / f"tech_{VERSION}_v1_ranks.csv", index=False)

import adapters, sentence_transformers, transformers  # noqa: E402,E401
(PROC / f"tech_{VERSION}_run.json").write_text(json.dumps({
    "version": VERSION, "date": date.today().isoformat(), "device": DEVICE,
    "models": {"topics": [SPECTER_BASE, SPECTER_DOC, SPECTER_QUERY], "cpc": PATENT_MODEL},
    "versions": {"torch": torch.__version__, "transformers": transformers.__version__,
                 "adapters": adapters.__version__, "sentence_transformers": sentence_transformers.__version__},
    "counts": {"engines": int(sentences.engine_name.nunique()), "sentences": len(sentences),
               "openalex_topics": len(topics), "cpc_main_groups": len(cpc)},
    "masked_name_tokens": masked_tokens, "centring": "mean vector of each set", "method": METHOD,
}, indent=2))

print("\nWhere the v1 choices rank, for reference only (median rank; share in top-50; share in top-200):")
for kind, d in cmp.groupby("kind"):
    for m in METHODS:
        r = d["rank_" + m]
        flag = "  <- used" if m == METHOD["oa" if kind == "openalex_topic" else "cpc"] else ""
        print(f"  {kind:15} {m:12} {r.median():6.0f} of {d.n_ranked.iloc[0]}   "
              f"{(r <= 50).mean():.0%}   {(r <= 200).mean():.0%}{flag}")
