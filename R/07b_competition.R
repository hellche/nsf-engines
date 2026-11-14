# Step 7b. Competitive landscape for each Engine's technology profile
#
# Output (data/processed/):
#   competition_states.csv     Engine x US state: profile patents (2021-2025 grants), share of US, LQ, rank;
#                              plus one row for the Engine's own region ("ENGINE REGION")
#   competition_countries.csv  Engine x inventor country: profile patents among US grants (2021-2025)
#   competition_papers.csv     Engine x country: OpenAlex works in the Engine's topics since the window start
#
# A patent counts for a state/country if at least one inventor lives there (counts overlap across states).

library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)
library(arrow)
library(httr2)

patent_dir <- Sys.getenv("PATENT_DIR", "/Users/elenachechik/Desktop/india/patent/data")
api_key    <- Sys.getenv("OPENALEX_API_KEY")
source(here("R", "regions.R"))

profile <- read_csv(here("data", "processed", "tech_profile.csv"), show_col_types = FALSE)
engines <- read_csv(here("data", "processed", "engines.csv"), show_col_types = FALSE)
regions <- load_regions()

cpc_tbl <- bind_rows(
  read_tsv_arrow(file.path(patent_dir, "raw", "cpc_official_24_25.tsv"),
                 col_select = c("patent_id", "cpc_subclass", "cpc_group")) |>
    mutate(patent_id = as.character(patent_id), cpc_main = str_remove(cpc_group, "/.*$")) |>
    select(patent_id, cpc_subclass, cpc_main),
  read_parquet(file.path(patent_dir, "2021_23", "cpc_21_23.parquet"))) |>
  distinct()

geo_all <- read_parquet(file.path(patent_dir, "inventors_pv_21_25_geo.parquet"),
                        col_select = c("publication_number", "state", "county", "country")) |>
  transmute(patent_id = publication_number, state, county, country) |> distinct()
geo_us <- geo_all |> filter(country == "US", !is.na(state))
state_totals <- geo_us |> distinct(patent_id, state) |> count(state, name = "state_all")
n_us <- n_distinct(geo_us$patent_id)

codes <- profile |> select(engine_name, cpc) |> filter(!is.na(cpc)) |>
  separate_longer_delim(cpc, delim = ";") |> mutate(cpc = str_trim(cpc)) |> distinct()
profile_ids <- \(e) { cc <- codes$cpc[codes$engine_name == e]
  unique(cpc_tbl$patent_id[cpc_tbl$cpc_subclass %in% cc[nchar(cc) == 4] | cpc_tbl$cpc_main %in% cc[nchar(cc) > 4]]) }

# ---- US states -------------------------------------------------------------------------------------

reg_pat <- in_region(geo_us |> mutate(name = NA_character_), regions) |> distinct(engine_name, patent_id)

states <- map_dfr(unique(codes$engine_name), \(e) {
  ids <- profile_ids(e)
  us_prof <- length(intersect(ids, geo_us$patent_id))
  by_state <- geo_us |> filter(patent_id %in% ids) |> distinct(patent_id, state) |>
    count(state, name = "patents") |> left_join(state_totals, by = "state") |>
    mutate(share_us = patents / us_prof, lq = (patents / state_all) / (us_prof / n_us))
  reg_ids <- reg_pat$patent_id[reg_pat$engine_name == e]
  reg_row <- tibble(state = "ENGINE REGION", patents = length(intersect(ids, reg_ids)),
                    state_all = length(reg_ids)) |>
    mutate(share_us = patents / us_prof, lq = (patents / state_all) / (us_prof / n_us))
  bind_rows(by_state, reg_row) |>
    mutate(engine_name = e, in_engine_states = state %in% regions$state[regions$engine_name == e],
           rank_patents = rank(-if_else(state == "ENGINE REGION", NA_real_, patents), na.last = "keep", ties.method = "min"),
           rank_lq = rank(-if_else(state == "ENGINE REGION" | patents < 20, NA_real_, lq), na.last = "keep", ties.method = "min"),
           across(c(share_us, lq), \(x) round(x, 3)))
}) |> relocate(engine_name) |> arrange(engine_name, desc(patents))

# rank the Engine's own region among states (by number of profile patents)
states <- states |> group_by(engine_name) |>
  mutate(rank_patents = if_else(state == "ENGINE REGION",
                                1L + sum(patents[state != "ENGINE REGION"] > patents[state == "ENGINE REGION"]),
                                as.integer(rank_patents))) |> ungroup()

# ---- Countries (US grants only: who invents for the US market) ------------------------------------------

countries <- map_dfr(unique(codes$engine_name), \(e) {
  ids <- profile_ids(e)
  geo_all |> filter(patent_id %in% ids, !is.na(country)) |> distinct(patent_id, country) |>
    count(country, name = "patents") |> mutate(share = round(patents / length(ids), 3), engine_name = e) |>
    arrange(desc(patents)) |> slice_head(n = 15)
}) |> relocate(engine_name)

# ---- Papers by country (OpenAlex group_by, $0.0001 per Engine) -------------------------------------------

topics <- profile |> filter(!is.na(topic_id)) |> group_by(engine_name) |>
  summarise(topic_ids = paste(unique(topic_id), collapse = "|"), .groups = "drop") |>
  left_join(engines |> select(engine_name, window_from), by = "engine_name")

papers <- pmap_dfr(topics, function(engine_name, topic_ids, window_from) {
  req <- request("https://api.openalex.org/works") |>
    req_url_query(filter = sprintf("topics.id:%s,from_publication_date:%s", topic_ids, as.Date(window_from)),
                  group_by = "authorships.countries") |>
    req_retry(max_tries = 20, is_transient = \(r) resp_status(r) %in% c(429, 503), backoff = \(i) 20)
  if (nzchar(api_key)) req <- req_url_query(req, api_key = api_key)
  res <- req_perform(req) |> resp_body_json(simplifyVector = FALSE)
  map_dfr(res$group_by, \(g) tibble(country = str_remove(g$key, "https://openalex.org/countries/"),
                                    country_name = g$key_display_name, works = g$count)) |>
    mutate(engine_name = engine_name, share = round(works / sum(works), 3)) |>
    arrange(desc(works)) |> slice_head(n = 15)
}) |> relocate(engine_name)

write_csv(states, here("data", "processed", "competition_states.csv"))
write_csv(countries, here("data", "processed", "competition_countries.csv"))
write_csv(papers, here("data", "processed", "competition_papers.csv"))

message("Engine regions among US states (profile patents, 2021-2025):")
states |> filter(state == "ENGINE REGION") |> select(engine_name, patents, share_us, lq, rank_patents) |> print(n = Inf)
