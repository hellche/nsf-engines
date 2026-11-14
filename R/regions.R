# Shared helpers: Engine regions (counties where known, otherwise whole states) and inventor geography
#
# data/manual/engine_regions.csv: one row per Engine x state (x county). An empty county means the whole
# state. Inventor geography comes from PatentsView (inventors_pv_21_25_geo.parquet: patent, name, state,
# county), built from g_inventor_disambiguated + g_location_disambiguated for 2021-2025 grants.

library(dplyr)
library(readr)
library(stringr)
library(here)
library(arrow)

load_regions <- function() {
  read_csv(here("data", "manual", "engine_regions.csv"), show_col_types = FALSE,
           col_types = cols(.default = "c")) |>
    mutate(county = na_if(str_trim(coalesce(county, "")), ""))
}

load_inventor_geo <- function(patent_dir) {
  read_parquet(file.path(patent_dir, "inventors_pv_21_25_geo.parquet"),
               col_select = c("publication_number", "name_first", "name_last", "state", "county", "country")) |>
    filter(country == "US", !is.na(state)) |>
    transmute(patent_id = publication_number, name = str_squish(paste(name_first, name_last)), state, county)
}

# inventor rows located in each Engine's region (adds engine_name)
in_region <- function(inv, regions = load_regions()) {
  whole <- regions |> filter(is.na(county)) |> distinct(engine_name, state)
  cnty  <- regions |> filter(!is.na(county)) |> distinct(engine_name, state, county)
  bind_rows(
    inner_join(inv, whole, by = "state", relationship = "many-to-many"),
    inner_join(inv, cnty, by = c("state", "county"), relationship = "many-to-many")
  )
}
