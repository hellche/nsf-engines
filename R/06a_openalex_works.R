# Step 6a. Publications of the knowledge base (OpenAlex), from the window start (5 years before the award)
#
# Two layers per Engine:
#   people        all works of the Engine's people with a reliable OpenAlex author match (step 3b)
#   institutions  works of the knowledge-producer partners (step 4) in the Engine's technology topics (step 5)
#
# Input:  data/processed/people_roles_evidence.csv, partners.csv, tech_profile.csv, engines.csv
# Output: data/raw/openalex_works/<query>.json     cached pages (one file per query)
#         data/processed/works_people.csv           person x work
#         data/processed/works_institutions.csv     Engine x work (+ which partner institutions, in-region flag)
#
# Cost: list queries, $0.0001 per page of 200 works; a full run is well under $0.10.

library(httr2)
library(jsonlite)
library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)

api_key  <- Sys.getenv("OPENALEX_API_KEY")
people   <- read_csv(here("data", "processed", "people_roles_evidence.csv"), show_col_types = FALSE)
partners <- read_csv(here("data", "processed", "partners.csv"), show_col_types = FALSE)
profile  <- read_csv(here("data", "processed", "tech_profile.csv"), show_col_types = FALSE)
engines  <- read_csv(here("data", "processed", "engines.csv"), show_col_types = FALSE)
cache_dir <- here("data", "raw", "openalex_works")
dir.create(cache_dir, showWarnings = FALSE, recursive = TRUE)

fields <- "id,doi,display_name,publication_year,publication_date,type,cited_by_count,primary_topic,topics,authorships"

# All pages of one filter, cached under a readable key
fetch_works <- function(key, filter) {
  f <- file.path(cache_dir, paste0(key, ".json"))
  if (file.exists(f)) return(read_json(f, simplifyVector = FALSE))
  out <- list(); cursor <- "*"
  repeat {
    req <- request("https://api.openalex.org/works") |>
      req_url_query(filter = filter, `per-page` = 200, cursor = cursor, select = fields) |>
      req_retry(max_tries = 30, is_transient = \(r) resp_status(r) %in% c(429, 503), backoff = \(i) 20)
    if (nzchar(api_key)) req <- req_url_query(req, api_key = api_key)
    res <- req_perform(req) |> resp_body_json(simplifyVector = FALSE)
    out <- c(out, res$results)
    cursor <- res$meta$next_cursor
    if (is.null(cursor) || length(res$results) == 0) break
  }
  write_json(out, f, auto_unbox = TRUE)
  out
}

oa_id <- function(x) str_remove(x %||% NA_character_, "https://openalex.org/")

works_table <- function(ws) map_dfr(ws, \(w) tibble(
  work_id   = oa_id(w$id),
  doi       = w$doi %||% NA_character_,
  title     = w$display_name %||% NA_character_,
  year      = w$publication_year %||% NA_integer_,
  type      = w$type %||% NA_character_,
  cited_by  = w$cited_by_count %||% NA_integer_,
  primary_topic = oa_id(w$primary_topic$id),
  topics    = paste(map_chr(w$topics %||% list(), \(t) oa_id(t$id)), collapse = ";"),
  subfields = paste(unique(map_chr(w$topics %||% list(), \(t) oa_id(t$subfield$id))), collapse = ";"),
  institutions = paste(unique(unlist(map(w$authorships %||% list(), \(a)
                   map_chr(a$institutions %||% list(), \(i) oa_id(i$id))))), collapse = ";"),
  n_authors = length(w$authorships %||% list())
))

window <- engines |> select(engine_name, window_from) |> mutate(window_from = as.character(as.Date(window_from)))

topics_by_engine <- profile |> filter(!is.na(topic_id)) |>
  group_by(engine_name) |>
  summarise(topic_ids = paste(unique(topic_id), collapse = "|"),
            subfield_ids = paste(unique(subfield_id), collapse = "|"), .groups = "drop")

# ---- 1. People: all works since the window start -----------------------------------------------

researchers <- people |>
  filter(in_team, reliable, !is.na(oa_id), !coalesce(check_merged, FALSE)) |>
  select(person_id, engine_name, name, role_suggested, oa_id) |>
  left_join(window, by = "engine_name") |>
  left_join(topics_by_engine, by = "engine_name")

works_people <- pmap_dfr(researchers, function(person_id, engine_name, name, role_suggested, oa_id,
                                               window_from, topic_ids, subfield_ids) {
  ws <- fetch_works(paste0("person_", person_id),
                    sprintf("authorships.author.id:%s,from_publication_date:%s", oa_id, window_from))
  if (!length(ws)) return(NULL)
  works_table(ws) |>
    mutate(person_id = person_id, engine_name = engine_name, name = name, role = role_suggested,
           in_engine_topics = str_detect(topics, topic_ids),
           in_engine_subfields = str_detect(subfields, subfield_ids), .before = 1)
})
write_csv(works_people, here("data", "processed", "works_people.csv"))

# ---- 2. Institutions: works of knowledge-producer partners in the Engine's topics ----------------

st_abbr <- c(Alabama = "AL", Missouri = "MO", Kansas = "KS", Alaska = "AK", Oregon = "OR", "North Carolina" = "NC",
             "South Carolina" = "SC", Indiana = "IN", Ohio = "OH", Connecticut = "CT", "West Virginia" = "WV",
             Pennsylvania = "PA", Iowa = "IA", Nebraska = "NE", "New York" = "NY", Maine = "ME",
             "New Hampshire" = "NH", Massachusetts = "MA", "Rhode Island" = "RI", Tennessee = "TN")
engine_states <- list(BRIDGES = c("AL", "TN"), "Critical Materials Crossroads" = c("MO", "KS"),
  "Critical Mineral Accelerator" = "AK", FAST = "OR", "Grid Modernization" = c("NC", "SC"), IMPACT = "IN",
  "NEO-SMART" = "OH", "Quantum Technologies" = "CT", RETI = c("WV", "PA"),
  "RuralSTAMINA Biomanufacturing" = c("IA", "NE"), STELLAR = "NY", Seafood = c("ME", "NH", "MA", "RI"))

producers <- partners |>
  filter(knowledge_producer == "yes", !is.na(oa_institution), !coalesce(oa_outlier, FALSE)) |>
  mutate(state_abbr = unname(st_abbr[state]),
         in_region = map2_lgl(engine_name, state_abbr, \(e, s) !is.na(s) && s %in% engine_states[[e]])) |>
  distinct(engine_name, oa_institution, partner, in_region)

works_inst <- producers |>
  group_by(engine_name) |>
  summarise(insts = paste(unique(oa_institution), collapse = "|"), .groups = "drop") |>
  left_join(window, by = "engine_name") |>
  left_join(topics_by_engine, by = "engine_name") |>
  pmap_dfr(function(engine_name, insts, window_from, topic_ids, subfield_ids) {
    key <- paste0("inst_", str_replace_all(str_to_lower(engine_name), "[^a-z]+", "-"))
    ws <- fetch_works(key, sprintf("institutions.id:%s,topics.id:%s,from_publication_date:%s",
                                   insts, topic_ids, window_from))
    if (!length(ws)) return(NULL)
    works_table(ws) |> mutate(engine_name = engine_name, .before = 1)
  })

# which partner institutions (and whether any in-region one) are on each work
inst_lookup <- producers |> group_by(engine_name, oa_institution) |>
  summarise(partner = first(partner), in_region = any(in_region), .groups = "drop")
works_inst <- works_inst |>
  mutate(inst_list = str_split(institutions, ";")) |>
  rowwise() |>
  mutate(partners_on_work = paste(inst_lookup$partner[inst_lookup$engine_name == engine_name &
                                                      inst_lookup$oa_institution %in% inst_list], collapse = "; "),
         any_in_region = any(inst_lookup$in_region[inst_lookup$engine_name == engine_name &
                                                   inst_lookup$oa_institution %in% inst_list])) |>
  ungroup() |> select(-inst_list)
write_csv(works_inst, here("data", "processed", "works_institutions.csv"))

# ---- Report -------------------------------------------------------------------------------------

message(sprintf("People works: %d rows (%d people); institution works: %d", nrow(works_people),
                n_distinct(works_people$person_id), nrow(works_inst)))
left_join(
  works_people |> group_by(engine_name) |>
    summarise(people = n_distinct(person_id), people_works = n_distinct(work_id),
              people_works_in_topics = n_distinct(work_id[in_engine_topics])),
  works_inst |> group_by(engine_name) |>
    summarise(inst_works_in_topics = n(), inst_works_in_region = sum(any_in_region)),
  by = "engine_name") |> print(n = Inf)
