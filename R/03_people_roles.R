# Step 3a. Classify people by the role they most likely play in the Engine's knowledge base
#
# Input:  data/processed/people_all.csv   (step 2)
#         data/manual/role_overrides.csv  (person_id, role, reason): manual decisions win over rules
# Output: data/processed/people_roles.csv
#
# Roles
#   researcher      produces research: faculty, scientists, research directors
#   research_admin  runs research at an institution that is (or could be) the science base:
#                   provost, VP/vice chancellor for research, dean, institute director
#   corporate_rd    leads R&D or technology in a company
#   organizer       everyone else: Engine executives without a research title, economic development,
#                   chambers, funds, investors, workforce and community roles, government
#
# Every person gets `rule_fired` (which rule assigned the role) and `needs_check` (TRUE when titles are
# missing or ambiguous). Step 3b adds OpenAlex evidence (publications) to confirm or revise the role.

library(dplyr)
library(stringr)
library(readr)
library(here)

people <- read_csv(here("data", "processed", "people_all.csv"), show_col_types = FALSE)
overrides <- read_csv(here("data", "manual", "role_overrides.csv"), show_col_types = FALSE,
                      col_types = cols(.default = "c"))

lc <- function(x) str_to_lower(coalesce(x, ""))

# ---- 1. Organisation type -------------------------------------------------------

engine_own <- regex(paste(
  "nsf .*engine", "engine$", "quantumct", "reti consortium", "critical materials crossroads",
  "neo-smart", "ruralstamina", sep = "|"), ignore_case = TRUE)

org_type_of <- function(org, domain) {
  o <- lc(org); d <- lc(domain)
  case_when(
    str_detect(o, "\\brtx\\b|intel\\b") ~ "company",                       # before "research center"
    str_detect(o, "university|college|institute of technology|school of|state colleges") ~ "academic",
    str_detect(o, "laboratory for laser|national lab|research institute|hudsonalpha|woods hole|sea grant|institute of optics|quantum institute|research center") ~ "academic_research",
    str_detect(o, "state of |department of|governor|commissioner|city of|business oregon") ~ "government",
    str_detect(o, "chamber|partnership|fund|alliance|association|council|hub|network|enterprise|accelerator|capital|ventures|innovations|nextcorps|conncorp|nexus|equity partners|bioconnect|fishermen|fisheries center|team neo|tech alliance|technology association") ~ "intermediary",
    str_detect(o, "mitre") ~ "nonprofit_rd",
    str_detect(o, "\\binc\\b|llc|corporation|company|\\bcorp\\b|intel|volkswagen|rtx|optimax|toptica|photonics|mining|genera|seed company|consult|pillsbury|lubrizol|grating|t\\.i\\.g") ~ "company",
    str_detect(d, "\\.edu$") ~ "academic",
    str_detect(d, "\\.gov$|oregon\\.gov") ~ "government",
    str_detect(d, "vw\\.com|aggrowtech|endolithmining|nana\\.com|ctinnovations") ~ "company",
    TRUE ~ NA_character_
  )
}

people <- people |>
  mutate(
    engine_staff = str_detect(coalesce(org_site, ""), engine_own) & !str_detect(lc(org_site), "university|college"),
    # Engine staff: the home organisation is read from the NSF email domain when available
    org_type = case_when(
      engine_staff & !is.na(email_domain) ~ org_type_of(NA, email_domain),
      engine_staff ~ "engine",
      TRUE ~ org_type_of(org_site, email_domain)
    ),
    org_type = coalesce(org_type, "unknown")
  )

# ---- 2. Role rules (first match wins) -------------------------------------------

title <- function(df) lc(paste(df$title_site, df$section_site))

re_admin  <- "provost|vice president for research|vice president, research|vice chancellor for research|vice chancellor for strategic|for research and innovation|executive director, research|\\bdean\\b|director of .*institute|founding director, center"
re_res    <- "professor|scientist|scientific officer|director of research|co-director of research|\\bco-i\\b|laser r&d|use-inspired r&d|director of engineering|crops|fractionation|construction materials|packaging"
re_tech   <- "chief technology|co-chief technology|\\bcto\\b|technology & innovation officer|r&d|research and development|director of grid innovation"

classified <- people |>
  mutate(t = title(pick(everything()))) |>
  mutate(
    role_rule = case_when(
      str_detect(t, re_admin) & org_type %in% c("academic", "academic_research", "engine") ~ "research_admin",
      str_detect(t, re_res) & org_type != "company"                                        ~ "researcher",
      str_detect(t, re_tech) & org_type == "company"                                       ~ "corporate_rd",
      str_detect(t, "scientist|director of research|co-director of research|director of engineering") &
        org_type == "company"                                                              ~ "corporate_rd",
      str_detect(t, re_tech)                                                               ~ "researcher",
      TRUE                                                                                 ~ "organizer"
    ),
    rule_fired = case_when(
      role_rule == "research_admin"                         ~ "title: research administration",
      role_rule == "researcher" & str_detect(t, re_res)     ~ "title: research",
      role_rule == "researcher"                             ~ "title: technology lead (not company)",
      role_rule == "corporate_rd"                           ~ "title: technology/research + company",
      TRUE                                                  ~ "default: no research title"
    ),
    no_title    = is.na(title_site) | title_site == "",
    needs_check = no_title |
      (role_rule == "organizer" & org_type %in% c("academic", "academic_research")) |
      rule_fired == "title: technology lead (not company)"
  ) |>
  select(-t)

# ---- 3. Manual overrides --------------------------------------------------------

roles <- classified |>
  left_join(rename(overrides, role_override = role, override_reason = reason), by = "person_id") |>
  mutate(
    role       = coalesce(role_override, role_rule),
    role_basis = if_else(!is.na(role_override), paste("manual:", override_reason), rule_fired)
  ) |>
  select(person_id, engine_name, name, role, role_basis, needs_check, org_type, title_site, org_site,
         role_nsf, former, in_nsf, in_site, in_team, email_domain, section_site, site_url, award_id)

write_csv(roles, here("data", "processed", "people_roles.csv"))

# ---- Report ---------------------------------------------------------------------

message(sprintf("People: %d; needs check: %d", nrow(roles), sum(roles$needs_check)))
roles |> filter(in_team) |> count(role) |> print()
roles |> filter(in_team) |> count(engine_name, role) |>
  tidyr::pivot_wider(names_from = role, values_from = n, values_fill = 0) |> print(n = Inf)
