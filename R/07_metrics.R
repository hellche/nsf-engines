# Step 7. Metrics per Engine (inputs for the reports)
#
# Output (data/processed/):
#   metrics_engine.csv        one row per Engine: people, partners, papers, patents, specialisation
#   metrics_patents_year.csv  Engine x grant year: regional patents in the technology profile
#   metrics_papers_year.csv   Engine x year: partner papers in the Engine's topics (all / in-region)
#   metrics_lq_cpc.csv        Engine x CPC code: regional patents, US patents, location quotient
#   metrics_top_assignees.csv Engine x assignee: top owners of the regional technology patents
#
# Location quotient (patents, 2021-2025 grants):
#   LQ = (region patents with the code / all region patents) / (US patents with the code / all US patents)
#   A patent belongs to a region if at least one inventor lives in the Engine's states (PatentsView).

library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)
library(arrow)

patent_dir <- Sys.getenv("PATENT_DIR", "/Users/elenachechik/Desktop/india/patent/data")
rd <- \(f) read_csv(here("data", "processed", f), show_col_types = FALSE)

engines  <- rd("engines.csv")
people   <- rd("people_roles_evidence.csv")
partners <- rd("partners.csv")
profile  <- rd("tech_profile.csv")
wp       <- rd("works_people.csv")
wi       <- rd("works_institutions.csv")
pe       <- rd("patents_engine.csv")

engine_states <- list(BRIDGES = c("AL", "TN"), "Critical Materials Crossroads" = c("MO", "KS"),
  "Critical Mineral Accelerator" = "AK", FAST = "OR", "Grid Modernization" = c("NC", "SC"), IMPACT = "IN",
  "NEO-SMART" = "OH", "Quantum Technologies" = "CT", RETI = c("WV", "PA"),
  "RuralSTAMINA Biomanufacturing" = c("IA", "NE"), STELLAR = "NY", Seafood = c("ME", "NH", "MA", "RI"))

# ---- People and partners ---------------------------------------------------------------------------

m_people <- people |> filter(in_team) |> group_by(engine_name) |>
  summarise(team = n(),
            in_nsf_award = sum(in_nsf),
            researchers = sum(role_suggested == "researcher"),
            research_admins = sum(role_suggested == "research_admin"),
            corporate_rd = sum(role_suggested == "corporate_rd"),
            organizers = sum(role_suggested == "organizer"),
            active_researchers = sum(coalesce(active_researcher, FALSE)), .groups = "drop")

inventors <- pe |> filter(team_inventor) |> distinct(engine_name, person_matched) |>
  count(engine_name, name = "team_inventors")

m_partners <- partners |> group_by(engine_name) |>
  summarise(partners = n(),
            partners_listed = sum(str_detect(source, "partner list")),
            knowledge_producers = sum(knowledge_producer == "yes"),
            companies = sum(knowledge_producer == "candidate"),
            partner_list_complete = !str_detect(first(completeness), "^Not available|Only|Core partners only"),
            .groups = "drop")

# ---- Papers ----------------------------------------------------------------------------------------

m_papers <- full_join(
  wp |> group_by(engine_name) |>
    summarise(people_with_works = n_distinct(person_id), people_works = n_distinct(work_id),
              people_works_in_topics = n_distinct(work_id[in_engine_topics]), .groups = "drop"),
  wi |> group_by(engine_name) |>
    summarise(partner_works_in_topics = n_distinct(work_id),
              partner_works_in_topics_region = n_distinct(work_id[any_in_region]), .groups = "drop"),
  by = "engine_name")

papers_year <- wi |> group_by(engine_name, year) |>
  summarise(works = n_distinct(work_id), works_in_region = n_distinct(work_id[any_in_region]), .groups = "drop")

# ---- Patents ---------------------------------------------------------------------------------------

m_patents <- pe |> group_by(engine_name) |>
  summarise(pat_region_tech = sum(region_tech),
            pat_region_tech_partner = sum(region_tech & partner_assignee),
            pat_partner_region = sum(partner_assignee & coalesce(invented_in_region, FALSE)),
            pat_partner_region_tech = sum(partner_assignee & coalesce(invented_in_region, FALSE) & in_tech_profile),
            pat_team_inventor = sum(team_inventor), .groups = "drop") |>
  mutate(share_region_tech_by_partners = round(pat_region_tech_partner / pat_region_tech, 3),
         share_partner_region_in_tech = round(pat_partner_region_tech / pat_partner_region, 3))

patents_year <- pe |> filter(region_tech) |> count(engine_name, grant_year, name = "patents")

top_assignees <- pe |> filter(region_tech) |>
  separate_longer_delim(assignees, delim = ";") |> mutate(assignee = str_squish(assignees)) |>
  filter(!is.na(assignee), assignee != "") |>
  count(engine_name, assignee, sort = TRUE) |>
  group_by(engine_name) |> slice_head(n = 10) |> ungroup()

# ---- Location quotient by CPC code ---------------------------------------------------------------------

cpc_tbl <- bind_rows(
  read_tsv_arrow(file.path(patent_dir, "raw", "cpc_official_24_25.tsv"),
                 col_select = c("patent_id", "cpc_subclass", "cpc_group")) |>
    mutate(patent_id = as.character(patent_id), cpc_main = str_remove(cpc_group, "/.*$")) |>
    select(patent_id, cpc_subclass, cpc_main),
  read_parquet(file.path(patent_dir, "2021_23", "cpc_21_23.parquet"))) |>
  distinct()

inv_states <- map_dfr(c(file.path(patent_dir, "2021_23", "inventors_pv_21_23.parquet"),
                        file.path(patent_dir, "inventors_pv_24_25.parquet")),
                      \(f) read_parquet(f, col_select = c("publication_number", "state", "country"))) |>
  filter(country == "US", !is.na(state)) |> distinct(patent_id = publication_number, state)

us_ids  <- unique(inv_states$patent_id)
n_us    <- length(us_ids)
codes <- profile |> select(engine_name, item, cpc) |> filter(!is.na(cpc)) |>
  separate_longer_delim(cpc, delim = ";") |> mutate(cpc = str_trim(cpc)) |> distinct(engine_name, cpc)

lq <- pmap_dfr(codes, function(engine_name, cpc) {
  region_ids <- unique(inv_states$patent_id[inv_states$state %in% engine_states[[engine_name]]])
  code_ids   <- unique(if (nchar(cpc) == 4) cpc_tbl$patent_id[cpc_tbl$cpc_subclass == cpc] else
                         cpc_tbl$patent_id[cpc_tbl$cpc_main == cpc])
  code_us    <- intersect(code_ids, us_ids)
  n_reg_code <- length(intersect(code_ids, region_ids))
  tibble(engine_name, cpc, region_patents = n_reg_code, region_all = length(region_ids),
         us_patents = length(code_us), us_all = n_us,
         lq = round((n_reg_code / length(region_ids)) / (length(code_us) / n_us), 2))
}) |> arrange(engine_name, desc(lq))

# profile-level LQ: all profile codes together (a patent counts once)
lq_profile <- map_dfr(names(engine_states), \(e) {
  cc <- codes$cpc[codes$engine_name == e]
  if (!length(cc)) return(tibble(engine_name = e, lq_profile = NA_real_))
  code_ids   <- unique(cpc_tbl$patent_id[cpc_tbl$cpc_subclass %in% cc[nchar(cc) == 4] | cpc_tbl$cpc_main %in% cc[nchar(cc) > 4]])
  region_ids <- unique(inv_states$patent_id[inv_states$state %in% engine_states[[e]]])
  tibble(engine_name = e,
         region_share_us_profile = round(length(intersect(code_ids, region_ids)) / length(intersect(code_ids, us_ids)), 4),
         lq_profile = round((length(intersect(code_ids, region_ids)) / length(region_ids)) /
                            (length(intersect(code_ids, us_ids)) / n_us), 2))
})

# ---- Combine and save -------------------------------------------------------------------------------------

metrics <- engines |>
  select(engine_name, acronym, region, lead_org, start_date, est_total_usd) |>
  left_join(m_people, by = "engine_name") |>
  left_join(inventors, by = "engine_name") |>
  left_join(m_partners, by = "engine_name") |>
  left_join(m_papers, by = "engine_name") |>
  left_join(m_patents, by = "engine_name") |>
  left_join(lq_profile, by = "engine_name") |>
  mutate(team_inventors = coalesce(team_inventors, 0L))

write_csv(metrics, here("data", "processed", "metrics_engine.csv"))
write_csv(patents_year, here("data", "processed", "metrics_patents_year.csv"))
write_csv(papers_year, here("data", "processed", "metrics_papers_year.csv"))
write_csv(lq, here("data", "processed", "metrics_lq_cpc.csv"))
write_csv(top_assignees, here("data", "processed", "metrics_top_assignees.csv"))

message("Metrics written for ", nrow(metrics), " Engines")
print(select(metrics, engine_name, active_researchers, knowledge_producers, partner_works_in_topics_region,
             pat_region_tech, lq_profile, share_region_tech_by_partners), n = Inf)
