# Step 6e. Researchers at the Engine's partner organisations
#
# The grant's PIs are mostly managers; the people who develop the technology often work at the partner
# universities and labs. Step 6a already downloads the works of the knowledge-producer partners in the
# Engine's technology topics (since the window start); each work lists its authors and their institutions.
# Here, for each Engine: authors with at least MIN_WORKS such works written AT a partner institution IN THE
# ENGINE'S STATES, the TOP with the most. In-region only: large partners elsewhere (e.g. Argonne for
# NEO-SMART) would otherwise fill the list, and the question is who develops the technology in the region.
# No new API calls (reads the step 6a cache). A partner without a state in partners.csv counts as not in
# the region (e.g. Kent State University for NEO-SMART: to be fixed in step 4).
#
# Input:  data/raw/openalex_works/inst_<engine>[__<version>].json   (step 6a, per PROFILE_VERSION)
#         data/processed/partners.csv, people_roles_evidence.csv, data/manual/engine_regions.csv
# Output: partner_researchers.csv (data/processed/ for v1, data/processed/profile_<version>/ otherwise):
#         Engine x author: works in the Engine's topics at an in-region partner, citations, years,
#         partner(s), whether the person is already in the team, most cited such work
# Run:    Rscript R/06e_partner_researchers.R          (PROFILE_VERSION=v3_1 for the v3.1 profile)

library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(jsonlite)
library(here)
source(here("R", "profile.R"))
source(here("R", "regions.R"))

MIN_WORKS <- 3      # works in the Engine's topics at a partner institution
TOP       <- 15     # researchers kept per Engine

version  <- profile_version()
partners <- read_csv(here("data", "processed", "partners.csv"), show_col_types = FALSE)
people   <- read_csv(here("data", "processed", "people_roles_evidence.csv"), show_col_types = FALSE)
regions  <- load_regions()
oa_id    <- \(x) str_remove(x %||% NA_character_, "https://openalex.org/")
`%||%`   <- function(x, y) if (is.null(x) || length(x) == 0) y else x   # cached nulls are {} (see 06a)

# knowledge-producer partners with an OpenAlex institution; in region = in one of the Engine's states
producers <- partners |>
  filter(knowledge_producer == "yes", !is.na(oa_institution), !coalesce(oa_outlier, FALSE)) |>
  mutate(state_abbr = state.abb[match(state, state.name)]) |>
  rowwise() |>
  mutate(in_region = !is.na(state_abbr) && state_abbr %in% regions$state[regions$engine_name == engine_name]) |>
  ungroup() |>
  distinct(engine_name, oa_institution, partner, in_region)

authors_of <- function(engine) {
  key <- paste0("inst_", str_replace_all(str_to_lower(engine), "[^a-z]+", "-"),
                if (version == "v1") "" else paste0("__", version))
  f <- here("data", "raw", "openalex_works", paste0(key, ".json"))
  if (!file.exists(f)) return(NULL)
  insts <- producers |> filter(engine_name == engine, in_region)
  if (!nrow(insts)) return(NULL)
  ws <- read_json(f, simplifyVector = FALSE)
  # one row per work x author x partner institution of that author on that work
  map_dfr(ws, \(w) map_dfr(w$authorships %||% list(), \(a) {
    inst <- map_chr(a$institutions %||% list(), \(i) oa_id(i$id))
    inst <- intersect(inst, insts$oa_institution)
    if (!length(inst) || !length(a$author$id)) return(NULL)   # authorships without an author id are skipped
    tibble(work_id = oa_id(w$id), title = w$display_name %||% NA_character_,
           year = w$publication_year %||% NA_integer_, cited_by = w$cited_by_count %||% 0L,
           author_id = oa_id(a$author$id), author = a$author$display_name %||% NA_character_,
           orcid = a$author$orcid %||% NA_character_, oa_institution = inst)
  })) |>
    left_join(insts |> select(-engine_name), by = "oa_institution") |>
    mutate(engine_name = engine)
}

aw <- map_dfr(unique(producers$engine_name), authors_of)
team_ids <- people |> filter(in_team, !is.na(oa_id)) |> distinct(engine_name, oa_id) |> mutate(in_team = TRUE)

researchers <- aw |>
  group_by(engine_name, author_id) |>
  summarise(name = names(which.max(table(author))),
            orcid = first(na.omit(orcid)),
            works_in_topics = n_distinct(work_id),
            citations = sum(cited_by[!duplicated(work_id)]),
            first_year = min(year, na.rm = TRUE), last_year = max(year, na.rm = TRUE),
            partners = paste(sort(unique(partner)), collapse = "; "),
            top_work = title[!duplicated(work_id)][which.max(cited_by[!duplicated(work_id)])],
            top_work_id = work_id[!duplicated(work_id)][which.max(cited_by[!duplicated(work_id)])],
            .groups = "drop") |>
  filter(works_in_topics >= MIN_WORKS) |>
  left_join(team_ids, by = c("engine_name", "author_id" = "oa_id")) |>
  mutate(in_team = coalesce(in_team, FALSE)) |>
  group_by(engine_name) |>
  arrange(desc(works_in_topics), desc(citations), .by_group = TRUE) |>
  slice_head(n = TOP) |>
  mutate(rank = row_number(), .after = engine_name) |>
  ungroup()

write_csv(researchers, proc_path("partner_researchers.csv"))
message(sprintf("Profile %s: %d researchers at in-region partners (>= %d works in the Engine's topics, top %d per Engine)",
                version, nrow(researchers), MIN_WORKS, TOP))
researchers |> count(engine_name, name = "researchers") |> print(n = Inf)
