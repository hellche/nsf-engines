# Step 1. Registry of NSF Regional Innovation Engines and the people named on the awards
#
# Input:  NSF Award Search API (https://api.nsf.gov/services/v1/awards.json), no key needed
# Output: data/raw/nsf_engines_awards_<cohort>.json  (raw API response, cached)
#         data/processed/engines.csv                 (one row per Engine award)
#         data/processed/people_nsf.csv              (one row per person x award: PI / Co-PI)
#
# A cohort is defined by the award start window. Cohort 2 = Type 2 awards starting in 2026.
# Engine awards are identified by the managing program element code 301Y00 (NSF Engines - Type 2).

library(httr2)
library(jsonlite)
library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)

cohort       <- 2
start_from   <- "01/01/2026"   # NSF API date format mm/dd/yyyy
start_to     <- "12/31/2026"
engines_pec  <- "301Y00"
raw_path     <- here("data", "raw", sprintf("nsf_engines_awards_cohort%d.json", cohort))
refresh      <- FALSE           # TRUE re-downloads even if the cached file exists

# ---- 1. Download (cached) -----------------------------------------------------

fetch_awards <- function(keyword, start_from, start_to, rpp = 25) {
  page <- function(offset) {
    request("https://api.nsf.gov/services/v1/awards.json") |>
      req_url_query(keyword = keyword, startDateStart = start_from,
                    startDateEnd = start_to, rpp = rpp, offset = offset) |>
      req_retry(max_tries = 3) |>
      req_perform() |>
      resp_body_json(simplifyVector = FALSE)
  }
  first <- page(1)
  total <- first$response$metadata$totalCount
  awards <- first$response$award
  offset <- 1 + rpp
  while (length(awards) < total) {
    nxt <- page(offset)$response$award
    if (length(nxt) == 0) break
    awards <- c(awards, nxt)
    offset <- offset + rpp
  }
  awards
}

if (refresh || !file.exists(raw_path)) {
  awards_raw <- fetch_awards('"NSF Engines"', start_from, start_to)
  write_json(awards_raw, raw_path, auto_unbox = TRUE, pretty = TRUE)
}
awards_raw <- read_json(raw_path, simplifyVector = FALSE)

# ---- 2. Engines table ---------------------------------------------------------

chr <- function(x) if (is.null(x)) NA_character_ else as.character(x)

# Some NSF titles use narrow no-break spaces (U+202F) and other Unicode spaces
squish_spaces <- function(x) str_squish(str_replace_all(x, "[\\h\\x{202F}\\x{00A0}]+", " "))

engines_all <- map_dfr(awards_raw, \(a) tibble(
  award_id          = chr(a$id),
  title             = chr(a$title),
  fund_program      = chr(a$fundProgramName),
  managing_pec      = chr(a$managingPec),
  lead_org          = chr(a$awardeeName),
  lead_city         = chr(a$awardeeCity),
  lead_state        = chr(a$awardeeStateCode),
  perf_city         = chr(a$perfCity),
  perf_state        = chr(a$perfStateCode),
  start_date        = chr(a$startDate),
  exp_date          = chr(a$expDate),
  est_total_usd     = as.numeric(chr(a$estimatedTotalAmt)),
  obligated_usd     = as.numeric(chr(a$fundsObligatedAmt)),
  program_officer   = chr(a$poName),
  abstract          = chr(a$abstractText)
))

engines <- engines_all |>
  filter(managing_pec == engines_pec, str_detect(fund_program, "Engines - Type 2")) |>
  mutate(
    cohort      = cohort,
    title       = squish_spaces(title),
    engine_name = str_match(title, "^NSF (.+?) Engine")[, 2],
    region      = str_trim(str_remove(str_match(title, " Engine in (.+)$")[, 2], "\\s*\\(.*\\)$")),
    region      = str_remove(region, "^the "),
    acronym     = str_match(title, "\\(([^)]+)\\)\\s*$")[, 2],
    start_date  = as.Date(start_date, "%m/%d/%Y"),
    exp_date    = as.Date(exp_date, "%m/%d/%Y"),
    window_from = start_date - lubridate::years(5)   # search window: 5 years before the award start
  ) |>
  relocate(cohort, award_id, engine_name, acronym, region, .before = 1) |>
  arrange(engine_name)

# ---- 3. People named on the awards -------------------------------------------

# NSF returns people as "First Middle Last email@domain"
parse_person <- function(s) {
  email <- str_extract(s, "\\S+@\\S+$")
  name  <- str_trim(str_remove(s, "\\S+@\\S+$"))
  tibble(name = name, email = email)
}

people_nsf <- map_dfr(awards_raw, \(a) {
  if (!identical(chr(a$managingPec), engines_pec)) return(NULL)
  pi    <- map_dfr(a$pi %||% list(), \(s) parse_person(s)) |> mutate(role_nsf = "PI")
  copi  <- map_dfr(a$coPDPI %||% list(), \(s) parse_person(s)) |> mutate(role_nsf = "Co-PI")
  bind_rows(pi, copi) |> mutate(award_id = chr(a$id))
}) |>
  semi_join(engines, by = "award_id") |>
  left_join(select(engines, award_id, engine_name, lead_org), by = "award_id") |>
  mutate(
    name         = squish_spaces(name),
    former       = str_detect(name, "\\(Former\\)"),   # NSF marks people replaced on the award
    name         = str_trim(str_remove(name, "\\s*\\(Former\\)")),
    email_domain = str_to_lower(str_extract(email, "(?<=@).+$")),
    source       = "NSF Award API",
    source_url   = paste0("https://www.nsf.gov/awardsearch/showAward?AWD_ID=", award_id)
  ) |>
  distinct(award_id, role_nsf, former, name, email, .keep_all = TRUE) |>   # NSF can list the same record twice
  select(-email) |>                                  # keep only the domain; personal addresses are not needed
  relocate(engine_name, award_id, role_nsf, former, name, email_domain, lead_org, .before = 1) |>
  arrange(engine_name, desc(role_nsf == "PI"), name)

# ---- 4. Save and report -------------------------------------------------------

write_csv(engines, here("data", "processed", "engines.csv"))
write_csv(people_nsf, here("data", "processed", "people_nsf.csv"))

message(sprintf("Engines (cohort %d): %d", cohort, nrow(engines)))
message(sprintf("People on awards: %d (PI %d, Co-PI %d; former %d)", nrow(people_nsf),
                sum(people_nsf$role_nsf == "PI"), sum(people_nsf$role_nsf == "Co-PI"),
                sum(people_nsf$former)))
print(select(engines, engine_name, acronym, region, lead_org, start_date, est_total_usd), n = Inf)
