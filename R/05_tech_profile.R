# Step 5. Technology profile of each Engine: 3-5 OpenAlex topics and CPC codes
#
# Input:  data/manual/tech_statements.csv    3-5 technology statements per Engine. Item 1 always comes from the
#                                             grant title (acronym expanded from the abstract); the rest from the
#                                             technical part of the abstract. Each row keeps a verbatim quote and
#                                             draft CPC codes (subclass "C22B" or main group "B29B17").
#         data/manual/tech_topic_choice.csv   manual choice of topic when the classifier's first topic is off
#         local USPTO grant files (PATENT_DIR) for checking that each CPC code has patents
# Output: data/raw/openalex_text_topics.json  cached classifier responses
#         data/processed/tech_topic_candidates.csv  top-3 OpenAlex topics per statement
#         data/processed/tech_profile.csv           one row per Engine x statement: topic, subfield, CPC, checks
#
# Why statements and not the whole abstract: the OpenAlex classifier labels the full NEO-SMART abstract as
# "Regional resilience and development" because most of the text is about the region, not the technology.

library(httr2)
library(jsonlite)
library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)
library(arrow)

statements <- read_csv(here("data", "manual", "tech_statements.csv"), show_col_types = FALSE)
choice     <- read_csv(here("data", "manual", "tech_topic_choice.csv"), show_col_types = FALSE,
                       col_types = cols(.default = "c")) |> mutate(item = as.integer(item))
api_key    <- Sys.getenv("OPENALEX_API_KEY")
patent_dir <- Sys.getenv("PATENT_DIR", "/Users/elenachechik/Desktop/india/patent/data")

# ---- 1. OpenAlex topic classification of each statement ($0.01 per call, cached) ------------

cache_path <- here("data", "raw", "openalex_text_topics.json")
cache <- if (file.exists(cache_path)) read_json(cache_path, simplifyVector = FALSE) else list()

classify <- function(text) {
  if (!is.null(cache[[text]])) return(cache[[text]])
  # new OpenAlex accounts spend their first $1 at most $0.10 per 5 minutes: wait and retry on 429
  req <- request("https://api.openalex.org/text/topics") |> req_body_json(list(title = text)) |>
    req_retry(max_tries = 40, is_transient = \(r) resp_status(r) %in% c(429, 503), backoff = \(i) 20) |>
    req_error(is_error = \(r) FALSE)
  if (nzchar(api_key)) req <- req_url_query(req, api_key = api_key)
  resp <- req_perform(req)
  if (resp_status(resp) != 200) {
    warning(sprintf("'%s': HTTP %d %s", text, resp_status(resp), substr(resp_body_string(resp), 1, 150)))
    return(list())
  }
  res <- resp_body_json(resp, simplifyVector = FALSE)
  cache[[text]] <<- res$topics
  write_json(cache, cache_path, auto_unbox = TRUE)
  res$topics
}

candidates <- statements |>
  mutate(topics = map(statement, classify)) |>
  select(engine_name, item, statement, topics) |>
  unnest_longer(topics, indices_to = "rank") |>
  mutate(topic_id    = str_remove(map_chr(topics, "id"), "https://openalex.org/"),
         topic       = map_chr(topics, "display_name"),
         score       = map_dbl(topics, "score"),
         subfield_id = str_remove(map_chr(topics, \(t) t$subfield$id), "https://openalex.org/"),
         subfield    = map_chr(topics, \(t) t$subfield$display_name),
         field       = map_chr(topics, \(t) t$field$display_name)) |>
  select(-topics)

write_csv(candidates, here("data", "processed", "tech_topic_candidates.csv"))

chosen <- candidates |>
  left_join(choice, by = c("engine_name", "item"), suffix = c("", "_manual")) |>
  filter(if_else(is.na(topic_id_manual), rank == 1, topic_id == topic_id_manual)) |>
  mutate(topic_basis = if_else(is.na(topic_id_manual),
                               sprintf("classifier rank 1 (score %.2f)", score),
                               paste("manual:", reason))) |>
  select(engine_name, item, topic_id, topic, subfield_id, subfield, field, topic_basis)

# ---- 2. CPC check: patents per code in the local USPTO grants, nationally and in the Engine's states --

engine_states <- tribble(
  ~engine_name,                     ~states,
  "BRIDGES",                        "AL|TN",
  "Critical Materials Crossroads",  "MO|KS",
  "Critical Mineral Accelerator",   "AK",
  "FAST",                           "OR",
  "Grid Modernization",             "NC|SC",
  "IMPACT",                         "IN",
  "NEO-SMART",                      "OH",
  "Quantum Technologies",           "CT",
  "RETI",                           "WV|PA",
  "RuralSTAMINA Biomanufacturing",  "IA|NE",
  "STELLAR",                        "NY",
  "Seafood",                        "ME|NH|MA|RI"
)

codes <- statements |>
  select(engine_name, item, cpc) |>
  separate_longer_delim(cpc, delim = ";") |>
  mutate(cpc = str_trim(cpc)) |>
  filter(!is.na(cpc), cpc != "") |>
  left_join(engine_states, by = "engine_name")

cpc_file  <- file.path(patent_dir, "raw", "cpc_official_24_25.tsv")
pat_files <- file.path(patent_dir, c("patents_2024_full_slim.parquet", "patents_2025_full_slim.parquet"))

if (file.exists(cpc_file) && all(file.exists(pat_files))) {
  cpc <- read_tsv_arrow(cpc_file, col_select = c("patent_id", "cpc_subclass", "cpc_group")) |>
    mutate(patent_id = as.character(patent_id), cpc_main = str_remove(cpc_group, "/.*$")) |>
    distinct(patent_id, cpc_subclass, cpc_main)
  # inventor states from PatentsView (the parsed location strings list each city once and cannot be
  # aligned with inventors); one row per patent x US state
  pv_file <- file.path(patent_dir, "inventors_pv_24_25.parquet")
  inv_states <- read_parquet(pv_file, col_select = c("publication_number", "state", "country")) |>
    filter(country == "US", !is.na(state)) |> distinct(patent_id = publication_number, state)

  count_code <- function(code, states) {
    ids <- if (nchar(code) == 4) cpc$patent_id[cpc$cpc_subclass == code] else cpc$patent_id[cpc$cpc_main == code]
    ids <- unique(ids)
    st  <- str_split(states, "\\|")[[1]]
    tibble(n_us = length(ids),
           n_region = n_distinct(inv_states$patent_id[inv_states$patent_id %in% ids & inv_states$state %in% st]))
  }
  codes <- codes |> mutate(res = map2(cpc, states, count_code)) |> unnest(res)
} else {
  warning("Local patent files not found; CPC counts skipped")
  codes <- codes |> mutate(n_us = NA_real_, n_region = NA_real_)
}

cpc_summary <- codes |>
  group_by(engine_name, item) |>
  summarise(cpc_patents_us_2024_25 = paste(sprintf("%s:%s", cpc, n_us), collapse = "; "),
            cpc_patents_region_2024_25 = paste(sprintf("%s:%s", cpc, n_region), collapse = "; "),
            cpc = paste(cpc, collapse = "; "),
            .groups = "drop")

# ---- 3. Profile -------------------------------------------------------------------------------

profile <- statements |>
  select(engine_name, item, source, statement, quote) |>
  left_join(chosen, by = c("engine_name", "item")) |>
  left_join(cpc_summary, by = c("engine_name", "item")) |>
  arrange(engine_name, item)

write_csv(profile, here("data", "processed", "tech_profile.csv"))

message(sprintf("Statements: %d; Engines: %d", nrow(profile), n_distinct(profile$engine_name)))
