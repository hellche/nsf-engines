# Step 6b. Patents of the knowledge base (local USPTO grant files)
#
# Three layers per Engine (a patent can be in several):
#   region_tech       an inventor lives in the Engine's states AND a CPC code is in the Engine's profile (step 5)
#   partner_assignee  an assignee is one of the Engine's partners (step 4), any technology
#   team_inventor     an inventor is one of the Engine's people (step 2), living in the Engine's states
#
# Input:  PATENT_DIR/patents_<year>_full_slim.parquet, PATENT_DIR/raw/cpc_official_24_25.tsv
#         data/processed/tech_profile.csv, partners.csv, people_roles_evidence.csv
# Output: data/processed/patents_engine.csv   Engine x patent with layer flags and matches
#
# Coverage: the local files currently hold grants of 2024-2025 (PATENT_YEARS). The window starts in 2021,
# so grants of 2021-2023 and pre-grant publications should be added when available.

library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)
library(arrow)

patent_dir   <- Sys.getenv("PATENT_DIR", "/Users/elenachechik/Desktop/india/patent/data")
patent_years <- as.integer(str_split(Sys.getenv("PATENT_YEARS", "2024,2025"), ",")[[1]])

profile  <- read_csv(here("data", "processed", "tech_profile.csv"), show_col_types = FALSE)
partners <- read_csv(here("data", "processed", "partners.csv"), show_col_types = FALSE)
people   <- read_csv(here("data", "processed", "people_roles_evidence.csv"), show_col_types = FALSE)

engine_states <- list(BRIDGES = c("AL", "TN"), "Critical Materials Crossroads" = c("MO", "KS"),
  "Critical Mineral Accelerator" = "AK", FAST = "OR", "Grid Modernization" = c("NC", "SC"), IMPACT = "IN",
  "NEO-SMART" = "OH", "Quantum Technologies" = "CT", RETI = c("WV", "PA"),
  "RuralSTAMINA Biomanufacturing" = c("IA", "NE"), STELLAR = "NY", Seafood = c("ME", "NH", "MA", "RI"))
all_states <- unique(unlist(engine_states))

# ---- Load patents ---------------------------------------------------------------------------------

pat <- map_dfr(patent_years, \(y) read_parquet(file.path(patent_dir, sprintf("patents_%d_full_slim.parquet", y)),
          col_select = c("patent_number", "application_date", "grant_date", "inventors",
                         "inventor_locations", "assignees", "assignee_locations"))) |>
  rename(patent_id = patent_number) |>
  mutate(grant_year = as.integer(str_sub(grant_date, 1, 4)))

# Grants 2021-2023: labeled files without inventor locations or dates (2021_23/patents_<year>_slim.parquet,
# made from patents_<year>_labeled.zip); CPC from PatentsView g_cpc_current (2021_23/cpc_21_23.parquet)
old_dir <- file.path(patent_dir, "2021_23")
old_files <- list.files(old_dir, pattern = "^patents_20(21|22|23)_slim\\.parquet$", full.names = TRUE)
# PatentsView subsets for the same grants (made from g_inventor/g_assignee_disambiguated):
# one row per inventor with city/state/country, and disambiguated assignee organisations
# Inventors with locations from PatentsView for ALL years (the same source keeps years comparable):
# 2021_23/inventors_pv_21_23.parquet and inventors_pv_24_25.parquet (made from g_inventor_disambiguated +
# g_location_disambiguated). The parsed location strings of the 2024-2025 files list each city once,
# so they cannot be aligned with inventors for ~45% of patents; they are only a fallback.
pv_inv_files <- c(file.path(old_dir, "inventors_pv_21_23.parquet"), file.path(patent_dir, "inventors_pv_24_25.parquet"))
pv_asg_file <- file.path(old_dir, "assignees_pv_21_23.parquet")
pv_inv <- map_dfr(pv_inv_files[file.exists(pv_inv_files)], \(f)
  read_parquet(f, col_select = c("publication_number", "name_first", "name_last", "state", "country"))) |>
  transmute(patent_id = publication_number, name = str_squish(paste(name_first, name_last)),
            state = if_else(country == "US", state, NA_character_))
pv_asg <- if (file.exists(pv_asg_file)) read_parquet(pv_asg_file) |>
  filter(!is.na(organization), organization != "") |>
  group_by(patent_id = publication_number) |>
  summarise(assignees_pv = paste(unique(organization), collapse = "; "), .groups = "drop") else NULL

if (length(old_files)) {
  old <- map_dfr(old_files, \(f) read_parquet(f)) |>
    transmute(patent_id = publication_number, grant_year = as.integer(grant_year), inventors, assignees = assignee)
  if (!is.null(pv_asg)) old <- old |> left_join(pv_asg, by = "patent_id") |>
    mutate(assignees = coalesce(assignees_pv, assignees)) |> select(-assignees_pv)
  pat <- bind_rows(pat, old)
}
pat <- pat |> filter(str_detect(patent_id, "^[0-9A-Z]+$")) |> distinct(patent_id, .keep_all = TRUE) |>
  mutate(has_location = !is.na(inventor_locations) | patent_id %in% pv_inv$patent_id)

cpc <- read_tsv_arrow(file.path(patent_dir, "raw", "cpc_official_24_25.tsv"),
                      col_select = c("patent_id", "cpc_subclass", "cpc_group")) |>
  mutate(patent_id = as.character(patent_id), cpc_main = str_remove(cpc_group, "/.*$")) |>
  distinct(patent_id, cpc_subclass, cpc_main)
if (file.exists(file.path(old_dir, "cpc_21_23.parquet"))) {
  cpc <- bind_rows(cpc, read_parquet(file.path(old_dir, "cpc_21_23.parquet"))) |> distinct()
}

# Inventors in long form with their state (inventors and locations are aligned by position)
inv <- pat |>
  select(patent_id, inventors, inventor_locations) |>
  mutate(name = str_split(inventors, ";\\s*"), loc = str_split(inventor_locations, ";\\s*")) |>
  select(-inventors, -inventor_locations) |>
  filter(lengths(name) == lengths(loc)) |>
  unnest_longer(c(name, loc)) |>
  mutate(state = str_match(loc, "-([A-Z]{2})-US$")[, 2]) |>
  select(patent_id, name, state) |>
  filter(!patent_id %in% pv_inv$patent_id) |>          # parsed strings only where PatentsView has no record
  bind_rows(pv_inv) |>
  filter(state %in% all_states)

# ---- 1. region_tech ---------------------------------------------------------------------------------

codes <- profile |> select(engine_name, cpc) |> filter(!is.na(cpc)) |>
  separate_longer_delim(cpc, delim = ";") |> mutate(cpc = str_trim(cpc)) |> distinct()

region_tech <- map_dfr(names(engine_states), \(e) {
  cc <- codes$cpc[codes$engine_name == e]
  if (!length(cc)) return(NULL)
  hits <- cpc |> filter(cpc_subclass %in% cc[nchar(cc) == 4] | cpc_main %in% cc[nchar(cc) > 4]) |>
    mutate(code = if_else(cpc_subclass %in% cc, cpc_subclass, cpc_main)) |>
    group_by(patent_id) |> summarise(cpc_matched = paste(unique(code), collapse = "; "), .groups = "drop")
  in_region <- inv |> filter(state %in% engine_states[[e]]) |>
    group_by(patent_id) |> summarise(n_inventors_region = n(), .groups = "drop")
  inner_join(hits, in_region, by = "patent_id") |> mutate(engine_name = e, region_tech = TRUE)
})

# ---- 2. partner_assignee ------------------------------------------------------------------------------

norm_org <- function(x) x |>
  stringi::stri_trans_general("Latin-ASCII") |> str_to_lower() |>
  str_replace_all("&", " and ") |> str_replace_all("[^a-z0-9 ]", " ") |>
  str_remove_all("\\b(the|inc|incorporated|corp|corporation|company|co|llc|l l c|ltd|limited|lp|plc|llp)\\b") |>
  str_squish()

partner_keys <- partners |> distinct(engine_name, partner, knowledge_producer, org_class) |>
  mutate(key = norm_org(partner)) |> filter(nchar(key) >= 3)

asg <- pat |> select(patent_id, assignees) |>
  mutate(assignee = str_split(assignees, ";\\s*")) |> select(-assignees) |>
  unnest_longer(assignee) |> mutate(akey = norm_org(assignee)) |> filter(akey != "")

# exact normalised name, or the assignee starts with a long partner name ("iowa state university research foundation")
exact  <- inner_join(asg, partner_keys, by = c("akey" = "key"), relationship = "many-to-many")
long_k <- partner_keys |> filter(nchar(key) >= 10)
prefix <- map_dfr(seq_len(nrow(long_k)), \(i) {
  k <- long_k$key[i]
  asg |> filter(str_starts(akey, fixed(paste0(k, " ")))) |>
    mutate(engine_name = long_k$engine_name[i], partner = long_k$partner[i],
           knowledge_producer = long_k$knowledge_producer[i], org_class = long_k$org_class[i])
})
partner_assignee <- bind_rows(exact, prefix) |>
  group_by(engine_name, patent_id) |>
  summarise(partner_matched = paste(unique(partner), collapse = "; "),
            partner_class = paste(unique(org_class), collapse = "; "), .groups = "drop") |>
  mutate(partner_assignee = TRUE)

# ---- 3. team_inventor ------------------------------------------------------------------------------------

clean_name <- function(x) x |> stringi::stri_trans_general("Latin-ASCII") |>
  str_remove_all("\\b(Dr|Prof)\\.?\\s+|,?\\s*\\b(PhD|Ph\\.D\\.|MBA|MS|Jr\\.?|Sr\\.?)\\b") |>
  str_replace_all("[^A-Za-z' -]", " ") |> str_squish() |> str_to_lower()
first_last <- function(x) { t <- str_split(clean_name(x), " "); tibble(
  first = map_chr(t, \(w) w[1]), last = map_chr(t, \(w) w[length(w)])) }

team <- people |> filter(in_team) |> select(engine_name, person_id, name) |>
  bind_cols(first_last(people$name[people$in_team]))
inv_n <- inv |> bind_cols(first_last(inv$name))

team_inventor <- map_dfr(names(engine_states), \(e) {
  t <- team |> filter(engine_name == e)
  inv_n |> filter(state %in% engine_states[[e]]) |>
    inner_join(t, by = "last", suffix = c("_inv", "_team"), relationship = "many-to-many") |>
    # full first name, or one is the start of the other ("rob"/"robert"); a first initial alone gives
    # false pairs (Claudia Reuter vs Charles Reuter)
    filter(first_inv == first_team |
             (nchar(first_inv) >= 3 & nchar(first_team) >= 3 &
                (str_starts(first_inv, first_team) | str_starts(first_team, first_inv)))) |>
    group_by(patent_id) |>
    summarise(engine_name = e, person_matched = paste(unique(name_team), collapse = "; "),
              inventor_as_listed = paste(unique(name_inv), collapse = "; "), .groups = "drop")
}) |> mutate(team_inventor = TRUE)

# ---- Combine ----------------------------------------------------------------------------------------------

patents_engine <- region_tech |>
  full_join(partner_assignee, by = c("engine_name", "patent_id")) |>
  full_join(team_inventor, by = c("engine_name", "patent_id")) |>
  mutate(across(c(region_tech, partner_assignee, team_inventor), \(x) coalesce(x, FALSE))) |>
  left_join(pat |> select(patent_id, grant_year, has_location, application_date, grant_date, assignees,
                          assignee_locations), by = "patent_id") |>
  relocate(engine_name, patent_id, region_tech, partner_assignee, team_inventor)

# tech match for partner and team patents too
tech_flag <- region_tech |> select(engine_name, patent_id) |> mutate(x = TRUE)
patents_engine <- patents_engine |>
  left_join(map_dfr(names(engine_states), \(e) {
    cc <- codes$cpc[codes$engine_name == e]
    cpc |> filter(cpc_subclass %in% cc[nchar(cc) == 4] | cpc_main %in% cc[nchar(cc) > 4]) |>
      distinct(patent_id) |> mutate(engine_name = e, in_tech_profile = TRUE)
  }), by = c("engine_name", "patent_id")) |>
  mutate(in_tech_profile = coalesce(in_tech_profile, FALSE)) |>
  select(-n_inventors_region)

# inventors living in the Engine's states, for every patent (partner patents are often filed elsewhere)
region_inv <- map_dfr(names(engine_states), \(e) inv |> filter(state %in% engine_states[[e]]) |>
  count(patent_id, name = "n_inventors_region") |> mutate(engine_name = e))
patents_engine <- patents_engine |>
  left_join(region_inv, by = c("engine_name", "patent_id")) |>
  mutate(n_inventors_region = if_else(has_location, coalesce(n_inventors_region, 0L), NA_integer_),
         invented_in_region = n_inventors_region > 0)   # NA only if a patent has no inventor locations

write_csv(patents_engine, here("data", "processed", "patents_engine.csv"))

message(sprintf("Patent years: %s; rows: %d", paste(patent_years, collapse = ","), nrow(patents_engine)))
patents_engine |> group_by(engine_name) |>
  summarise(n_region_tech = sum(region_tech),
            n_partner = sum(partner_assignee),
            n_partner_in_tech = sum(partner_assignee & in_tech_profile),
            n_partner_in_region = sum(partner_assignee & invented_in_region, na.rm = TRUE),
            n_partner_in_region_tech = sum(partner_assignee & invented_in_region & in_tech_profile, na.rm = TRUE),
            n_team_inventor = sum(team_inventor)) |>
  print(n = Inf)
