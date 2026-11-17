# Shared helpers: which technology profile the data steps (6a, 6b, 6d, 7, 7b) and the site use
#
# PROFILE_VERSION (environment variable) picks the profile:
#   v1    (default) manual statements, R/05_tech_profile.R -> data/processed/tech_profile.csv
#   v3_1  core of profile v3.1, py/05v3_1c_core.py -> data/processed/tech_profile_v3_1_core.csv (rows in_core),
#         1-2 OpenAlex topics and CPC main groups per technology of the grant
#
# Files that depend on the profile are kept per version: v1 in data/processed/ (as before),
# other versions in data/processed/profile_<version>/. Everything else (Engines, people, partners) is shared.
#
# Usage: PROFILE_VERSION=v3_1 Rscript R/06a_openalex_works.R

library(dplyr)
library(readr)
library(stringr)
library(here)

PROFILE_VERSIONS <- c("v1", "v3_1")
PROFILE_LABELS   <- c(v1 = "v1", v3_1 = "v3.1")
PROFILE_SITE_DIR <- c(v1 = "", v3_1 = "v3")   # site: v1 in docs/, v3.1 in docs/v3/ (R/08_render_site.R)

profile_version <- function() {
  v <- Sys.getenv("PROFILE_VERSION", "v1")
  if (!v %in% PROFILE_VERSIONS) stop("PROFILE_VERSION must be one of: ", paste(PROFILE_VERSIONS, collapse = ", "))
  v
}

PROFILE_FILES <- c("works_people.csv", "works_institutions.csv", "patents_engine.csv", "patents_team.csv",
                   "metrics_engine.csv", "metrics_patents_year.csv", "metrics_papers_year.csv",
                   "metrics_lq_cpc.csv", "metrics_top_assignees.csv",
                   "competition_states.csv", "competition_countries.csv", "competition_papers.csv")

# path of a processed file for the given profile version (creates the version folder when writing)
proc_path <- function(f, version = profile_version()) {
  if (version == "v1" || !f %in% PROFILE_FILES) return(here("data", "processed", f))
  d <- here("data", "processed", paste0("profile_", version))
  dir.create(d, showWarnings = FALSE)
  file.path(d, f)
}

# The profile in one form for all versions: one row per Engine x item x code, with
#   item         statement (v1) or technology of the grant (v3_1)
#   item_label   statement / technology label
#   topic_id, topic, subfield_id   OpenAlex topic (NA on CPC rows)
#   cpc          CPC subclass ("C22B") or main group ("C22B7"), as in the patent files (NA on topic rows)
load_profile <- function(version = profile_version()) {
  if (version == "v1") {
    p <- read_csv(here("data", "processed", "tech_profile.csv"), show_col_types = FALSE)
    topics <- p |> filter(!is.na(topic_id)) |>
      transmute(engine_name, item, item_label = statement, topic_id, topic, subfield_id)
    cpc <- p |> filter(!is.na(cpc)) |> select(engine_name, item, item_label = statement, cpc) |>
      tidyr::separate_longer_delim(cpc, delim = ";") |> mutate(cpc = str_trim(cpc)) |> filter(cpc != "")
    return(bind_rows(topics, cpc))
  }
  core <- read_csv(here("data", "processed", "tech_profile_v3_1_core.csv"), show_col_types = FALSE) |>
    filter(in_core)
  # subfield ids of the topics, from the OpenAlex topic list (cached by py/00_reference_lists.py / 05v2a)
  tl <- jsonlite::read_json(here("data", "raw", "openalex_topics.json"), simplifyVector = FALSE)
  sub <- tibble(topic_id = str_remove(vapply(tl, \(t) t$id, ""), "https://openalex.org/"),
                subfield_id = str_remove(vapply(tl, \(t) t$subfield$id, ""), "https://openalex.org/"))
  bind_rows(
    core |> filter(kind == "oa") |>
      transmute(engine_name, item = tech_id, item_label = tech_label, topic_id = item_id, topic = item_title) |>
      left_join(sub, by = "topic_id"),
    core |> filter(kind == "cpc") |>
      transmute(engine_name, item = tech_id, item_label = tech_label, cpc = str_remove(item_id, "/.*$"))
  )
}

# CPC codes of the profile: one row per Engine x code
profile_codes <- function(profile) profile |> filter(!is.na(cpc)) |> distinct(engine_name, cpc)
