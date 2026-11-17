# NSF Regional Innovation Engines: knowledge bases

What scientific and technological base does each of the 12 NSF Regional Innovation Engines (Cohort 2,
awards from 2026) stand on? We trace it from the people and partners the Engine names itself to their
papers and patents in the Engine's technology, from five years before the award onward.

**Site:** https://hellche.github.io/nsf-engines/ (Pipeline, Methodology, a page per Engine, Publications, Patents)

## Approach

1. **Who:** people on the NSF award and on the Engine's website; their roles; OpenAlex author profiles.
2. **Partners:** organisations from the Engine's website, matched to ROR and OpenAlex; knowledge producers.
3. **Technology profile:** what the Engine works on, as OpenAlex topics (papers) and CPC groups (patents).
4. **Output:** papers of the team and partners in the profile's topics; patents of the region and the
   team in the profile's CPC groups.
5. **Metrics:** team and partner output, regional patent location quotients, competing states, the
   region's industries.

## Technology profile: where we are

| Version | How it is chosen | Status |
|---|---|---|
| v1 | 3-5 statements per Engine written by hand; topics from the OpenAlex classifier, CPC codes by hand | used by all metrics on the site |
| v2 | every OpenAlex topic and CPC group ranked by embedding similarity to all sentences of the grant | rankings only, for comparison |
| v3.1 | science and technology fragments of the grant grouped into 2-5 technologies; per technology, rank fusion of embeddings with an independent signal (OpenAlex classifier, BM25 on CPC text); a judge with a fixed rubric for what the fusion cannot confirm and as an audit | **core ready**: 128 items for 39 technologies (`data/processed/tech_profile_v3_1_core.csv`) |

The fragment extraction and the judge scores of v3.1 were made in a chat session, not through an API, and
are not reproducible; every core item records its basis. Details: `HANDOFF.md`, the Methodology page.

## Next

1. Recompute the metrics (steps 6-7) with the v3.1 profile; needs the local USPTO patent files.
2. A version switch on the site (v1 / v2 / v3.1) and a comparison page.
3. Optionally: the v3.1 extraction and judge through the API, three runs each, to check stability.

## Run order

| Step | Script |
|---|---|
| Engines and NSF people; people from Engine sites; roles; OpenAlex authors | `R/01_engines_registry.R`, `R/02_people_site.R`, `R/03_people_roles.R`, `R/03b_openalex_people.R` |
| Partners | `R/04_partners.R` |
| Technology profile v1 | `R/05_tech_profile.R` |
| Reference lists (CPC titles, OpenAlex topics) | `py/00_reference_lists.py` |
| Technology profile v2 / v3.1 | `py/05v2a_embed_rank.py v2_1` and `v3_1`, `py/05v3_1b_fuse.py`, `py/05v3_1c_core.py` |
| Papers; patents; paper details; team patents | `R/06a_openalex_works.R`, `R/06b_patents.R`, `R/06c_works_details.R`, `R/06d_team_patents.R` |
| Metrics; competition; economic base | `R/07_metrics.R`, `R/07b_competition.R`, `R/07c_economy.R` |
| Site (`docs/`) | `R/08_render_site.R` (also run by GitHub Actions on every push to `main`) |

Python only for the profile steps (`.venv`, Python 3.12+). Keys: `OPENALEX_API_KEY` in `~/.Renviron`.
Local data not in git: USPTO/PatentsView parquet files (`PATENT_DIR`), caches in `data/raw/`.

## Data sources

NSF Award Search API; Engine websites; OpenAlex (authors, institutions, works, topics, topic classifier);
ROR; USPTO grants 2021-2025 with PatentsView tables; CPC Title List 2026.08; County Business Patterns 2023.
