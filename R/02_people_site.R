# Step 2. People named on each Engine's website, merged with the people on the NSF award
#
# Input:  data/processed/people_nsf.csv        (step 1)
#         data/manual/people_site.csv          (curated from each Engine's site; one row per person x page,
#                                               source_url and retrieved date on every row)
#         data/manual/person_aliases.csv       (same person under different names, with the reason)
# Output: data/processed/people_all.csv        (one row per person x Engine, NSF and site combined)
#
# Matching within an Engine: same last name and compatible first name (same first name, a known
# nickname, or the site's first name equals the NSF middle initial), plus the manual alias table.

library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)

people_nsf  <- read_csv(here("data", "processed", "people_nsf.csv"), show_col_types = FALSE)
people_site <- read_csv(here("data", "manual", "people_site.csv"), show_col_types = FALSE)
aliases     <- read_csv(here("data", "manual", "person_aliases.csv"), show_col_types = FALSE)

# ---- Name normalisation -------------------------------------------------------

nicknames <- tribble(
  ~short,    ~full,
  "nick",    "nicholas",  "rob",  "robert",   "bob",   "robert",  "jim",   "james",
  "matt",    "matthew",   "mike", "michael",  "greg",  "gregory", "liz",   "elizabeth",
  "jake",    "jacob",     "sam",  "samuel",   "tom",   "thomas",  "christi", "christina",
  "steve",   "stephen",   "steve", "steven",  "dan",   "daniel",  "rich",  "richard",
  "ben",     "benjamin",  "jon",  "jonathan", "jeff",  "jeffrey", "deb",   "deborah",
  "skip",    "warren",    "larry", "lawrence", "fred", "frederick", "jen", "jennifer"
)

clean_name <- function(x) {
  x |>
    stringi::stri_trans_general("Latin-ASCII") |>
    str_remove_all("\\b(Dr|Mr|Ms|Mrs|Prof)\\.?\\s+") |>
    str_remove_all(",?\\s*\\b(PhD|Ph\\.D\\.|MBA|MS|MDiv|P\\.Eng\\.?|Jr\\.?|Sr\\.?)\\b\\.?") |>
    str_replace_all("[^A-Za-z' -]", " ") |>
    str_squish() |>
    str_to_lower()
}

name_parts <- function(x) {
  tok <- str_split(clean_name(x), " ")
  tibble(
    first  = map_chr(tok, 1),
    middle = map_chr(tok, \(t) if (length(t) > 2) t[2] else NA_character_),
    last   = map_chr(tok, \(t) t[length(t)])
  )
}

canon_first <- function(f) coalesce(nicknames$full[match(f, nicknames$short)], f)

first_compatible <- function(f_nsf, m_nsf, f_site) {
  canon_first(f_nsf) == canon_first(f_site) |
    (!is.na(m_nsf) & str_sub(m_nsf, 1, 1) == str_sub(f_site, 1, 1) & nchar(m_nsf) == 1) |
    (!is.na(m_nsf) & nchar(f_nsf) == 1 & m_nsf == f_site) |                  # "S. Pamir Alpay" vs "Pamir Alpay"
    str_starts(f_nsf, fixed(f_site)) | str_starts(f_site, fixed(f_nsf))      # "lee" vs "lee ann"
}

# ---- Candidate matches by last name within an Engine --------------------------

nsf_keys <- people_nsf |>
  mutate(row_nsf = row_number()) |>
  bind_cols(name_parts(people_nsf$name)) |>
  select(row_nsf, engine_name, name_nsf = name, first_n = first, middle_n = middle, last_n = last)

site_keys <- people_site |>
  mutate(row_site = row_number()) |>
  bind_cols(name_parts(people_site$name_site)) |>
  select(row_site, engine_name, name_site, first_s = first, last_s = last)

auto_matches <- inner_join(nsf_keys, site_keys, by = "engine_name", relationship = "many-to-many") |>
  filter(last_n == last_s | str_detect(last_n, fixed(last_s)) | str_detect(last_s, fixed(last_n))) |>
  filter(first_compatible(first_n, middle_n, first_s)) |>
  transmute(engine_name, name_nsf, name_site, match_rule = "last name + first name")

alias_matches <- aliases |> transmute(engine_name, name_nsf, name_site, match_rule = "manual alias")

matches <- bind_rows(alias_matches, auto_matches) |>
  distinct(engine_name, name_nsf, name_site, .keep_all = TRUE)

# ---- One row per person x Engine ---------------------------------------------

nsf_side <- people_nsf |>
  group_by(engine_name, name) |>
  summarise(
    role_nsf     = paste(unique(role_nsf), collapse = "; "),
    former       = all(former),                     # TRUE only if every NSF listing is "former"
    email_domain = first(email_domain),
    award_id     = first(award_id),
    .groups = "drop"
  ) |>
  rename(name_nsf = name)

site_side <- people_site |>
  group_by(engine_name, name_site) |>
  summarise(
    title_site   = paste(unique(na.omit(title_site)), collapse = "; "),
    org_site     = paste(unique(na.omit(org_site)), collapse = "; "),
    section_site = paste(unique(section_site), collapse = "; "),
    in_team      = any(in_team),
    site_url     = first(source_url),
    retrieved    = first(retrieved),
    .groups = "drop"
  )

people_all <- nsf_side |>
  left_join(matches, by = c("engine_name", "name_nsf")) |>
  full_join(site_side, by = c("engine_name", "name_site")) |>
  mutate(
    name         = coalesce(name_site, name_nsf),
    in_nsf       = !is.na(name_nsf),
    in_site      = !is.na(name_site),
    in_team      = coalesce(in_team, FALSE) | in_nsf,
    source       = case_when(in_nsf & in_site ~ "NSF + site", in_nsf ~ "NSF only", TRUE ~ "site only"),
    person_id    = sprintf("%s__%s", str_replace_all(str_to_lower(engine_name), "[^a-z]+", "-"),
                           str_replace_all(clean_name(name), " ", "-"))
  ) |>
  select(person_id, engine_name, name, name_nsf, name_site, source, in_nsf, in_site, in_team,
         role_nsf, former, title_site, org_site, section_site, email_domain, match_rule,
         award_id, site_url, retrieved) |>
  arrange(engine_name, desc(in_nsf), name)

write_csv(people_all, here("data", "processed", "people_all.csv"))

# ---- Report ---------------------------------------------------------------------

message(sprintf("People (person x Engine): %d; in team: %d", nrow(people_all), sum(people_all$in_team)))
people_all |>
  count(engine_name, source) |>
  pivot_wider(names_from = source, values_from = n, values_fill = 0) |>
  print(n = Inf)

message("NSF people not found on the Engine's site (check manually):")
people_all |> filter(source == "NSF only") |> select(engine_name, name, role_nsf, former, email_domain) |> print(n = Inf)
