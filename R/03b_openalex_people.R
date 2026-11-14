# Step 3b. OpenAlex evidence for each person: is this person an active researcher?
#
# Input:  data/processed/people_roles.csv (step 3a), data/processed/engines.csv (step 1)
# Output: data/raw/openalex_people/<person_id>.json  (cached API responses, one file per person)
#         data/processed/people_openalex.csv           (best OpenAlex author match + evidence per person)
#         data/processed/people_roles_evidence.csv     (roles from 3a + evidence + suggested role)
#
# API key: put OPENALEX_API_KEY=... in ~/.Renviron (free key, $1/day). Without a key the shared budget
# is $0.10/day per IP, roughly 100 author searches. One author search costs $0.001.
#
# Matching: OpenAlex author search by name; a candidate counts only if the last name matches and the
# first name is compatible. Among those, a candidate whose affiliations contain the person's
# organisation (from the site or the NSF e-mail domain) is preferred. The match quality is recorded.

library(httr2)
library(jsonlite)
library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)

roles   <- read_csv(here("data", "processed", "people_roles.csv"), show_col_types = FALSE)
engines <- read_csv(here("data", "processed", "engines.csv"), show_col_types = FALSE)
cache_dir <- here("data", "raw", "openalex_people")
dir.create(cache_dir, showWarnings = FALSE, recursive = TRUE)

api_key  <- Sys.getenv("OPENALEX_API_KEY")
only     <- Sys.getenv("ONLY_ENGINE")      # optional: limit a run to one Engine, e.g. ONLY_ENGINE=NEO-SMART
min_works_5y <- 5                          # publications since the window start to count as active

# ---- Helpers --------------------------------------------------------------------

clean <- function(x) x |>
  stringi::stri_trans_general("Latin-ASCII") |>
  str_remove_all("\\b(Dr|Prof)\\.?\\s+") |>
  str_remove_all(",?\\s*\\b(PhD|Ph\\.D\\.|MBA|MS|MDiv)\\b\\.?") |>
  str_replace_all("[^A-Za-z' -]", " ") |> str_squish() |> str_to_lower()

# JSON nulls come back as NULL from the API but as empty lists from the cache
scalar_chr <- function(x) if (length(x) == 0 || is.list(x)) NA_character_ else as.character(x)

first_last <- function(x) {                 # "S. Pamir Alpay" -> "pamir alpay", "Lee A Munk" -> "lee munk"
  t <- str_split(clean(x), " ")[[1]]
  t <- t[nchar(t) > 1 | length(t) <= 2]
  paste(t[1], t[length(t)])
}

oa_get <- function(path, query) {
  req <- request(paste0("https://api.openalex.org/", path)) |> req_url_query(!!!query)
  if (nzchar(api_key)) req <- req_url_query(req, api_key = api_key)
  req |> req_retry(max_tries = 3, is_transient = \(r) resp_status(r) %in% c(429, 503)) |>
    req_error(is_error = \(r) FALSE) |> req_perform()
}

search_author <- function(person_id, name) {
  f <- file.path(cache_dir, paste0(person_id, ".json"))
  if (file.exists(f)) return(read_json(f, simplifyVector = FALSE))
  resp <- oa_get("authors", list(search = first_last(name), `per-page` = 10))
  if (resp_status(resp) != 200) {
    warning(sprintf("%s: HTTP %d (budget exhausted?)", name, resp_status(resp)))
    return(NULL)
  }
  out <- resp_body_json(resp, simplifyVector = FALSE)$results
  write_json(out, f, auto_unbox = TRUE)
  out
}

# ---- The person's organisation(s) ---------------------------------------------------
# 1) ROR ids: ROR affiliation matching (free API), only when ROR marks the match as "chosen".
#    Engine staff are also matched to the Engine's lead organisation.
# 2) Phrase: the organisation's full name without legal suffixes must appear inside an OpenAlex
#    institution name ("lubrizol" in "Lubrizol (United States)"). Single words are not enough:
#    "Cleveland" from "Greater Cleveland Partnership" must not match "Cleveland Clinic".

ror_cache_path <- here("data", "raw", "ror_cache.csv")
ror_cache <- if (file.exists(ror_cache_path)) read_csv(ror_cache_path, show_col_types = FALSE,
                                                       col_types = cols(.default = "c")) else
  tibble(org = character(), ror = character())

ror_chosen <- function(org) {
  if (is.na(org) || org == "") return(NA_character_)
  hit <- ror_cache$ror[ror_cache$org == org]
  if (length(hit)) return(hit[1])
  resp <- request("https://api.ror.org/v2/organizations") |> req_url_query(affiliation = org) |>
    req_retry(max_tries = 3) |> req_perform() |> resp_body_json(simplifyVector = FALSE)
  chosen <- keep(resp$items, \(it) isTRUE(it$chosen))
  ror <- if (length(chosen)) chosen[[1]]$organization$id else NA_character_
  ror_cache <<- bind_rows(ror_cache, tibble(org = org, ror = ror))
  write_csv(ror_cache, ror_cache_path)
  ror
}

org_phrase <- function(org) {
  p <- clean(org) |>
    str_remove_all("\\b(the|inc|llc|corporation|corp|company|co|ltd|retired)\\b") |> str_squish()
  if (nchar(p) < 4) NA_character_ else p
}

person_orgs <- function(org_site, lead_org, engine_staff) {
  orgs <- str_trim(str_split(coalesce(org_site, ""), ";|\\band\\b")[[1]])
  orgs <- orgs[orgs != "" & !str_detect(orgs, regex("engine|consortium|quantumct|crossroads|ruralstamina|neo-smart", TRUE))]
  if (engine_staff || length(orgs) == 0) orgs <- c(orgs, lead_org)
  list(ror = na.omit(map_chr(orgs, ror_chosen)), phrase = na.omit(map_chr(orgs, org_phrase)))
}

evaluate_candidates <- function(cands, name, keys, window_year) {
  if (length(cands) == 0) return(NULL)
  target <- str_split(first_last(name), " ")[[1]]
  map_dfr(cands, \(a) {
    nm   <- str_split(clean(a$display_name), " ")[[1]]
    alts <- map_chr(a$display_name_alternatives %||% list(), \(x) clean(x))
    last_ok  <- nm[length(nm)] == target[2] | any(str_ends(alts, paste0(" ", target[2])))
    first_ok <- str_sub(nm[1], 1, 1) == str_sub(target[1], 1, 1)
    # current institutions (last known) vs any institution in the author's history
    matches_org <- function(inst_list) {
      nms  <- unique(map_chr(inst_list, \(i) i$display_name %||% ""))
      rors <- unique(na.omit(map_chr(inst_list, \(i) scalar_chr(i$ror))))
      txt  <- clean(paste(nms, collapse = " | "))
      any(rors %in% keys$ror) || (length(keys$phrase) > 0 && any(str_detect(txt, fixed(keys$phrase))))
    }
    inst_now  <- matches_org(a$last_known_institutions %||% list())
    inst_past <- matches_org(map(a$affiliations %||% list(), "institution"))
    inst_ok   <- inst_now || inst_past
    cby <- a$counts_by_year %||% list()
    works_5y <- sum(map_int(cby, \(y) if (y$year >= window_year) as.integer(y$works_count) else 0L))
    tibble(
      oa_id = str_remove(a$id, "https://openalex.org/"), oa_name = a$display_name,
      orcid = scalar_chr(a$orcid), works_count = a$works_count, cited_by = a$cited_by_count,
      h_index = as.integer(scalar_chr(a$summary_stats$h_index)), works_5y = works_5y,
      last_inst = paste(map_chr(a$last_known_institutions %||% list(), \(i) i$display_name %||% ""), collapse = "; "),
      top_topics = paste(head(map_chr(a$topics %||% list(), \(t) t$display_name), 3), collapse = "; "),
      name_ok = last_ok & first_ok, inst_ok = inst_ok, inst_now = inst_now
    )
  }) |> filter(name_ok)
}

# Manual rejections of specific OpenAlex authors (merged or wrong profiles)
rejects_path <- here("data", "manual", "openalex_rejects.csv")
rejects <- if (file.exists(rejects_path)) read_csv(rejects_path, show_col_types = FALSE) else
  tibble(person_id = character(), oa_id = character(), reason = character())

# ---- Run --------------------------------------------------------------------------

todo <- roles |>
  filter(in_team, is.na(only) | only == "" | engine_name == only) |>
  left_join(select(engines, engine_name, lead_org, window_from), by = "engine_name") |>
  mutate(engine_staff = org_type == "engine" | str_detect(coalesce(org_site, ""),
                          regex("engine|consortium|quantumct|crossroads|ruralstamina|neo-smart", TRUE)))

evidence <- pmap_dfr(todo, function(person_id, name, org_site, lead_org, engine_staff, window_from, ...) {
  cands <- search_author(person_id, name)
  if (is.null(cands)) return(tibble(person_id = person_id, match_quality = "not queried"))
  keys  <- person_orgs(org_site, lead_org, engine_staff)
  ev    <- evaluate_candidates(cands, name, keys, as.integer(format(as.Date(window_from), "%Y")))
  if (!is.null(ev)) ev <- filter(ev, !oa_id %in% rejects$oa_id[rejects$person_id == person_id])
  if (is.null(ev) || nrow(ev) == 0) return(tibble(person_id = person_id, match_quality = "no name match"))
  best <- ev |> arrange(desc(inst_now), desc(inst_ok), desc(works_count)) |> slice(1)
  quality <- case_when(
    best$inst_now               ~ "name + institution",
    best$inst_ok                ~ "name + past institution only",
    nrow(ev) == 1               ~ "name only (single candidate)",
    TRUE                        ~ sprintf("name only (ambiguous: %d candidates)", nrow(ev))
  )
  best |> mutate(person_id = person_id, match_quality = quality, n_candidates = nrow(ev), .before = 1)
})

write_csv(evidence, here("data", "processed", "people_openalex.csv"))

# ---- Combine with roles and suggest -----------------------------------------------

combined <- roles |>
  left_join(evidence, by = "person_id") |>
  mutate(
    reliable = match_quality %in% c("name + institution"),
    # very high recent output often means OpenAlex merged several people into one profile
    check_merged = reliable & coalesce(works_5y, 0) > 150,
    active_researcher = reliable & coalesce(works_5y, 0) >= min_works_5y,
    role_suggested = case_when(
      role %in% c("research_admin", "corporate_rd") ~ role,             # title-based roles stay
      active_researcher                            ~ "researcher",
      role == "researcher" & reliable & coalesce(works_5y, 0) == 0 ~ "organizer",
      TRUE                                         ~ role
    ),
    evidence_note = case_when(
      is.na(match_quality) | match_quality == "not queried" ~ "OpenAlex not queried",
      !reliable ~ paste("OpenAlex:", match_quality),
      TRUE ~ sprintf("OpenAlex %s: %d works since window start, h=%s", oa_id, works_5y, h_index)
    )
  )

write_csv(combined, here("data", "processed", "people_roles_evidence.csv"))

message(sprintf("Queried: %d; matched by name + institution: %d; active researchers: %d",
                sum(evidence$match_quality != "not queried"),
                sum(combined$reliable, na.rm = TRUE), sum(combined$active_researcher, na.rm = TRUE)))
combined |> filter(in_team, !is.na(match_quality)) |>
  count(role, role_suggested) |> print()
