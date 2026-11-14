# NSF Regional Innovation Engines: knowledge base of each Engine

Reproducible pipeline that finds the scientific and technological base of each NSF Regional Innovation
Engine (Cohort 2, awards starting in 2026) from the people and partners named by the Engine itself.

Search window for papers and patents: from 5 years before the award start onward.

## Steps

| # | Step | Script | Output |
|---|---|---|---|
| 1 | Engines and people on the NSF awards (PI, Co-PI) | `R/01_engines_registry.R` | `data/processed/engines.csv`, `data/processed/people_nsf.csv` |
| 2 | People named on each Engine's website, merged with NSF people | `R/02_people_site.R` + `data/manual/people_site.csv` | `data/processed/people_all.csv` |
| 3a | Classify people by title and organisation: researcher / research_admin / corporate_rd / organizer | `R/03_people_roles.R` (+ `data/manual/role_overrides.csv`) | `data/processed/people_roles.csv` |
| 3b | OpenAlex evidence per person (author match via name + ROR/organisation, works since window start) | `R/03b_openalex_people.R` | `data/processed/people_roles_evidence.csv` |
| 4 | Partners from each Engine's website (+ team members' organisations); ROR match, org class, knowledge producers, OpenAlex output | `R/04_partners.R` + `data/manual/partners_site.csv`, `partner_sources.csv`, `partner_aliases.csv` | `data/processed/partners.csv` |
| 5 | Technology profile: 3-5 statements per Engine -> OpenAlex topics + CPC codes, checked against patents | `R/05_tech_profile.R` + `data/manual/tech_statements.csv`, `tech_topic_choice.csv` | `data/processed/tech_profile.csv`, `tech_topic_candidates.csv` |
| 6a | Papers (OpenAlex): all works of matched people; works of knowledge-producer partners in the Engine's topics | `R/06a_openalex_works.R` | `data/processed/works_people.csv`, `works_institutions.csv` |
| 6b | Patents (local USPTO grants): region x technology, partner assignees, team inventors | `R/06b_patents.R` | `data/processed/patents_engine.csv` |
| 7 | Metrics per Engine: people, partners, papers, patents, patent location quotients | `R/07_metrics.R` | `data/processed/metrics_*.csv` |
| 7b | Competition: US states and the Engine's region ranked by profile patents and LQ; inventor countries (patents); author countries (OpenAlex papers) | `R/07b_competition.R` | `data/processed/competition_*.csv` |
| 7c | Economic base: employment and LQ of related industries (County Business Patterns 2023) | `R/07c_economy.R` + `data/manual/engine_naics.csv` | `data/processed/economy_engine.csv` |
| 8 | Per-Engine reports (parameterised Rmd) and index page -> `docs/` for GitHub Pages | `R/08_render_site.R`, `reports/engine_report.Rmd`, `reports/index.Rmd` | `docs/*.html` |

## Data sources

- NSF Award Search API, no key: https://api.nsf.gov/services/v1/awards.json
- OpenAlex API (free key), SciSciNet-v2 link tables (paper -> NSF award, paper -> patent)
- USPTO grant full texts (local parquet) joined with PatentsView bulk tables
  (disambiguated inventors and assignees, county FIPS, non-patent references, pre-grant publications)

## Notes on step 1

- Cohort 2 Engine awards are found by keyword "NSF Engines", start date in 2026 and program element code 301Y00.
- NSF marks people replaced on an award as "(Former)"; they are kept with `former = TRUE`.
- Raw API responses are cached in `data/raw/` (not tracked); set `refresh <- TRUE` to re-download.

## Notes on step 2

- Engine websites are listed in `data/manual/engine_sites.csv`. NSF does not link them; they were found
  through news releases and The Engine's Builder Platform pages.
- `data/manual/people_site.csv` is curated by hand from each site's team pages (retrieved 2026-11-14).
  Every row keeps its `source_url`. `in_team = FALSE` marks people only quoted on the site (governors, mayors).
- Same person under different names is resolved automatically (last name + first name, nicknames, middle
  initials) and through `data/manual/person_aliases.csv`, which records the reason for each alias.
- Not yet extracted: RETI full org chart, STELLAR collaborators page, partner pages of all Engines (step 4).

## Notes on step 3

- 3a assigns a role from titles and organisation type with explicit rules; `rule_fired` says which rule,
  `needs_check` flags missing or ambiguous titles. Manual decisions go to `data/manual/role_overrides.csv`.
- 3b needs `OPENALEX_API_KEY` in `~/.Renviron` for a full run (about 160 author searches, ~$0.16 of the
  free $1/day). Without a key it uses the shared $0.10/day IP budget; `ONLY_ENGINE=NEO-SMART` limits a run.
- An OpenAlex author is accepted only when the name matches and an affiliation matches the person's
  organisation: by ROR id (ROR affiliation matching, "chosen" only) or by the organisation's full name
  as a phrase. Single words are not enough ("Greater Cleveland Partnership" must not match "Cleveland Clinic").
  Unmatched or ambiguous people keep their 3a role and are listed for manual review.
- Reliable match = the affiliation matches among the author's CURRENT (last known) institutions.
  A match only in past affiliations is recorded as "name + past institution only" and not used.
- OpenAlex sometimes merges namesakes into one profile: `check_merged` flags > 150 works in the window,
  and `data/manual/openalex_rejects.csv` rejects specific wrong profiles (with the reason).
- `role_suggested`: an organizer with a reliable match and >= 5 works since the window start becomes
  a researcher; research_admin and corporate_rd keep their title-based role and get the evidence attached.

## Notes on step 4

- Partner lists come from each Engine's site (`partner_sources.csv` records page, date and completeness).
  BRIDGES, IMPACT and Seafood show partners only as logo images; Grid Modernization and Quantum publish
  no list. For all Engines, organisations of team members are added as partners ("team member").
- Logo-derived names were lightly normalised when transcribing (e.g. "OSU Logo" -> Oregon State University);
  abbreviations and sub-units are mapped in `partner_aliases.csv` (with an optional manual ROR id).
- ROR matching: "chosen" match AND name similarity >= 0.6 with at least one shared distinctive word
  AND a US location (unless the partner is clearly foreign). Rejected matches are kept in `ror_rejected`.
  Knowledge producers without a ROR match get a fallback OpenAlex institution search (US only).
- `knowledge_producer`: yes = university, national lab, research institute, research hospital;
  candidate = company (to be checked with patents in step 6); no = everything else.
- `oa_works_5y` = OpenAlex works of the institution since the window start. `oa_outlier` flags implausible
  totals (PNNL: ~270k works/year in OpenAlex, an institution-lineage error).

## Notes on step 5

- Each Engine gets 3-5 technology statements. Item 1 always comes from the grant title (acronym expanded
  from the abstract; IMPACT's title is not informative and is noted as such); the others come from the
  technical part of the abstract. Every statement keeps a verbatim quote.
- Whole abstracts are not classified: OpenAlex labels the full NEO-SMART abstract "Regional resilience and
  development". Each statement is classified separately with OpenAlex `/text/topics` ($0.01 per call);
  the top-3 candidates are kept, rank 1 is used unless `tech_topic_choice.csv` says otherwise (with reason).
- CPC codes are drafted per statement at subclass level (C22B) or main group (B29B17) and checked against
  the local USPTO grants 2024-2025: patents per code in the US and with an inventor in the Engine's states.

## Notes on step 6

- Papers: window = 5 years before the award start onward. People layer uses only reliable author matches
  (not flagged as merged). Institution layer = knowledge-producer partners with an OpenAlex institution
  (PNNL excluded as an outlier) x the Engine's topics (`topics.id`, any of a work's 3 topics).
  `any_in_region` = at least one partner institution on the work is in the Engine's states.
- Patents: grants 2021-2025. 2024-2025 from `patents_<year>_full_slim.parquet`; 2021-2023 from the labeled
  files in `PATENT_DIR/2021_23` (slim parquet copies made from the zips), CPC from PatentsView
  `g_cpc_current` (`cpc_21_23.parquet`), assignees from `assignees_pv_21_23.parquet`.
- Inventor locations for ALL years come from PatentsView (`inventors_pv_21_23.parquet`,
  `inventors_pv_24_25.parquet`, built from `g_inventor_disambiguated` + `g_location_disambiguated`), so the
  years are comparable. The location strings of the 2024-2025 files list each city once and could not be
  aligned with inventors for ~45% of patents; they are used only where PatentsView has no record.
  Pre-grant publications are not included. Region = an inventor's state in the Engine's states.
  Partner assignees are matched on normalised names (exact, or the assignee starts with a partner name of
  10+ characters). Team inventors need the same last name, full first name (or prefix) and an inventor
  address in the Engine's states; common names (e.g. Kevin Moore) still need a manual check.
- Partner companies such as Intel or Goodyear patent nationwide: use `invented_in_region` and
  `in_tech_profile` to keep the regional, on-topic part.

## Notes on steps 7-8

- Regions are defined in `data/manual/engine_regions.csv` (`R/regions.R`): counties where the list is known
  (NEO-SMART: 18 Northeast Ohio counties; STELLAR: 11 counties listed in the NSF abstract), otherwise whole
  states. Inventor counties come from PatentsView (`inventors_pv_21_25_geo.parquet`).
- Patent location quotient: (region patents with the code / all region patents) / (US patents with the code /
  all US patents), 2021-2025 grants.
- Economic base: County Business Patterns 2023 files (cbp23co/st/us) downloaded from census.gov into
  `data/raw/cbp/` (the Census API now requires a key). Related industries per Engine are chosen from the NSF
  abstract in `data/manual/engine_naics.csv`. CBP 2023 uses noise-infused values for small cells.
- Partner assignee matching does not yet include subsidiaries and IP holding companies (e.g. SWIMC LLC for
  Sherwin-Williams), so partner shares are lower bounds.
- Run order: 01 -> 02 -> 03 -> 03b -> 04 -> 05 -> 06a -> 06b -> 07 -> 07b -> 07c -> 08. `docs/` is ready for GitHub Pages
  (publish from the `docs` folder of the main branch).
