# Step 6d. Patents of the Engine's team members, one row per person x patent, with titles
#
# Takes the team-inventor patents found in step 6b (team_inventor = TRUE) and adds the patent title from the
# local USPTO files: patents_<year>_full_slim.parquet for 2024-2025, patents_<year>_labeled.zip for 2021-2023
# (the slim 2021-2023 copies have no titles).
#
# Input:  data/processed/patents_engine.csv, people_roles_evidence.csv, PATENT_DIR files above
# Output: patents_team.csv   engine x person x patent (per PROFILE_VERSION, see R/profile.R: the in_tech_profile flag
#         depends on the profile)
#
# Matching of team members to inventors (step 6b) uses last name, first name and an address in the Engine's
# states; common names (e.g. Kevin Moore) can still be namesakes, so `inventor_as_listed` is kept for checks.

library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)
source(here("R", "profile.R"))   # PROFILE_VERSION: which technology profile; per-version outputs
library(arrow)

patent_dir <- Sys.getenv("PATENT_DIR", "/Users/elenachechik/Desktop/india/patent/data")

pe <- read_csv(proc_path("patents_engine.csv"),
               col_types = cols(patent_id = col_character(), .default = col_guess())) |>
  filter(team_inventor)
people <- read_csv(here("data", "processed", "people_roles_evidence.csv"), show_col_types = FALSE) |>
  filter(in_team) |> select(engine_name, person_id, name)

# Titles: 2024-2025 from the slim parquet files, 2021-2023 from the labeled zips (read only two columns)
ids <- unique(pe$patent_id)
new_titles <- map_dfr(c(2024, 2025), \(y)
  read_parquet(file.path(patent_dir, sprintf("patents_%d_full_slim.parquet", y)),
               col_select = c("patent_number", "title")) |>
    filter(patent_number %in% ids) |> rename(patent_id = patent_number))
old_titles <- map_dfr(2021:2023, \(y)
  read_csv(file.path(patent_dir, "2021_23", sprintf("patents_%d_labeled.zip", y)),
           col_select = c("publication_number", "title"), col_types = cols(.default = col_character())) |>
    filter(publication_number %in% ids) |> rename(patent_id = publication_number))
titles <- bind_rows(new_titles, old_titles) |> distinct(patent_id, .keep_all = TRUE)

team_patents <- pe |>
  separate_longer_delim(person_matched, "; ") |>
  rename(name = person_matched) |>
  left_join(people, by = c("engine_name", "name")) |>
  left_join(titles, by = "patent_id") |>
  transmute(engine_name, person_id, name, patent_id, grant_year, title, assignees,
            in_tech_profile = coalesce(in_tech_profile, FALSE), cpc_matched,
            invented_in_region, inventor_as_listed) |>
  arrange(engine_name, name, desc(grant_year), patent_id)

write_csv(team_patents, proc_path("patents_team.csv"))
message(sprintf("Team patents: %d person x patent rows, %d patents, %d people; titles found: %d; unmatched people: %d",
                nrow(team_patents), n_distinct(team_patents$patent_id), n_distinct(team_patents$person_id),
                sum(!is.na(team_patents$title)), sum(is.na(team_patents$person_id))))
