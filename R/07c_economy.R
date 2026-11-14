# Step 7c. Economic base of each Engine's region: employment in related industries (County Business Patterns)
#
# Input:  data/raw/cbp/cbp23co.txt, cbp23st.txt, cbp23us.txt  (CBP 2023, census.gov, downloaded by hand)
#         data/manual/engine_naics.csv     related NAICS industries per Engine, with rationale
#         data/manual/engine_regions.csv   counties where known, otherwise states
#         PATENT_DIR/inventors_pv_21_25_geo.parquet  only to map county names to FIPS codes
# Output: data/processed/economy_engine.csv  Engine x NAICS: regional employment, establishments, share, LQ
#
# Employment LQ = (region employment in the industry / region total employment) /
#                 (US employment in the industry / US total employment)
# CBP 2023 publishes noise-infused values instead of suppressing cells; small counties can be imprecise.

library(dplyr)
library(readr)
library(stringr)
library(purrr)
library(here)
library(arrow)

patent_dir <- Sys.getenv("PATENT_DIR", "/Users/elenachechik/Desktop/india/patent/data")
cbp_dir <- here("data", "raw", "cbp")
source(here("R", "regions.R"))
regions <- load_regions()
naics   <- read_csv(here("data", "manual", "engine_naics.csv"), show_col_types = FALSE, col_types = cols(.default = "c"))

# CBP codes: "325///" (3-digit), "3255//" (4-digit), "------" (all industries)
cbp_code <- \(n) if_else(n == "00", "------", str_pad(n, 6, "right", "/"))

co <- read_csv(file.path(cbp_dir, "cbp23co.txt"), show_col_types = FALSE,
               col_select = c("fipstate", "fipscty", "naics", "emp", "est"), col_types = cols(.default = "c")) |>
  mutate(across(c(emp, est), as.numeric))
st <- read_csv(file.path(cbp_dir, "cbp23st.txt"), show_col_types = FALSE,
               col_select = c("fipstate", "naics", "lfo", "emp", "est"), col_types = cols(.default = "c")) |>
  filter(lfo == "-") |> mutate(across(c(emp, est), as.numeric))
us <- read_csv(file.path(cbp_dir, "cbp23us.txt"), show_col_types = FALSE,
               col_select = c("naics", "lfo", "emp", "est"), col_types = cols(.default = "c")) |>
  filter(lfo == "-") |> mutate(across(c(emp, est), as.numeric))

# state abbreviation -> FIPS, county name -> FIPS (from PatentsView locations)
geo <- read_parquet(file.path(patent_dir, "inventors_pv_21_25_geo.parquet"),
                    col_select = c("state", "county", "state_fips", "county_fips", "country")) |>
  filter(country == "US", !is.na(state_fips)) |> distinct(state, county, state_fips, county_fips)
state_fips <- geo |> distinct(state, state_fips) |> filter(!is.na(state_fips)) |> distinct(state, .keep_all = TRUE)
county_fips <- geo |> filter(!is.na(county_fips), !is.na(county)) |> distinct(state, county, .keep_all = TRUE) |>
  mutate(county_fips = str_pad(county_fips, 3, "left", "0"), state_fips = str_pad(state_fips, 2, "left", "0"))

region_cbp <- function(e, code) {
  r <- regions |> filter(engine_name == e)
  whole <- r |> filter(is.na(county)) |> left_join(state_fips, by = "state") |>
    mutate(state_fips = str_pad(state_fips, 2, "left", "0"))
  cnty  <- r |> filter(!is.na(county)) |> left_join(county_fips |> select(state, county, state_fips, county_fips),
                                                     by = c("state", "county"))
  a <- st |> filter(fipstate %in% whole$state_fips, naics == code)
  b <- co |> filter(paste(fipstate, fipscty) %in% paste(cnty$state_fips, cnty$county_fips), naics == code)
  tibble(emp = sum(a$emp, b$emp, na.rm = TRUE), est = sum(a$est, b$est, na.rm = TRUE),
         n_counties_found = nrow(distinct(b, fipstate, fipscty)), n_counties_listed = nrow(cnty))
}

us_total <- us$emp[us$naics == "------"]

economy <- naics |>
  mutate(code = cbp_code(naics)) |>
  pmap_dfr(function(engine_name, naics, label, rationale, code) {
    reg <- region_cbp(engine_name, code)
    tot <- region_cbp(engine_name, "------")
    us_ind <- us$emp[us$naics == code]
    tibble(engine_name, naics, label,
           region_emp = reg$emp, region_est = reg$est, region_total_emp = tot$emp,
           us_emp = us_ind, region_share_of_us = round(reg$emp / us_ind, 4),
           lq_emp = round((reg$emp / tot$emp) / (us_ind / us_total), 2),
           counties = if (reg$n_counties_listed > 0) sprintf("%d of %d", tot$n_counties_found, reg$n_counties_listed) else "whole state(s)",
           rationale)
  })

write_csv(economy, here("data", "processed", "economy_engine.csv"))
message("CBP 2023 economic base written")
economy |> select(engine_name, naics, label, region_emp, lq_emp, counties) |> print(n = Inf)
