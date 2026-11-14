# Step 4. Partners of each Engine: who is likely part of the knowledge base?
#
# Input:  data/manual/partners_site.csv     (partners as listed on each Engine's site, by the site's category)
#         data/manual/partner_sources.csv   (page, retrieval date and completeness per Engine)
#         data/processed/people_roles.csv   (step 3a: organisations of team members, used as extra partners)
# Output: data/raw/ror_partners_cache.csv, data/raw/openalex_institutions.json (caches)
#         data/processed/partners.csv       (one row per partner x Engine)
#
# Classification
#   1. ROR affiliation matching ("chosen" matches only) gives an identifier, ROR types and location.
#   2. org_class from ROR types, name patterns and the site's own category.
#   3. knowledge_producer:
#        "yes"        research universities, national labs, research institutes, research hospitals (ROR)
#        "candidate"  companies: R&D unknown until patents are checked (step 6)
#        "no"         government, intermediaries, investors, philanthropy, K-12 and community colleges
#   4. OpenAlex institution record for ROR-matched partners: works since the window start.

library(httr2)
library(jsonlite)
library(dplyr)
library(tidyr)
library(stringr)
library(purrr)
library(readr)
library(here)

partners_raw <- read_csv(here("data", "manual", "partners_site.csv"), show_col_types = FALSE)
roles        <- read_csv(here("data", "processed", "people_roles.csv"), show_col_types = FALSE)
engines      <- read_csv(here("data", "processed", "engines.csv"), show_col_types = FALSE)
api_key      <- Sys.getenv("OPENALEX_API_KEY")

clean <- function(x) x |>
  stringi::stri_trans_general("Latin-ASCII") |>
  str_replace_all("[–—]", "-") |> str_squish()

# ---- 1. Partners from the sites + organisations of team members ---------------------

team_orgs <- roles |>
  filter(in_team, !org_type %in% c("engine", "unknown")) |>
  select(engine_name, org_site) |>
  separate_longer_delim(org_site, delim = ";") |>
  mutate(partner_raw = str_trim(str_remove(org_site, "\\s*\\(implied\\)")),
         category_site = "Team member organisation") |>
  filter(partner_raw != "", !str_detect(partner_raw, "Consultant|retired")) |>
  select(engine_name, category_site, partner_raw)

aliases <- read_csv(here("data", "manual", "partner_aliases.csv"), show_col_types = FALSE)
team_orgs <- bind_rows(team_orgs,
  tibble(engine_name = "BRIDGES", category_site = "Team member organisation", partner_raw = "Alabama A&M University"))

partners <- bind_rows(mutate(partners_raw, source = "partner list"),
                      mutate(team_orgs, source = "team member")) |>
  left_join(select(aliases, partner_raw, partner_canonical), by = "partner_raw") |>
  mutate(partner = clean(coalesce(partner_canonical, partner_raw)),
         key = str_to_lower(str_remove_all(partner, "[^A-Za-z0-9]"))) |>
  group_by(engine_name, key) |>
  summarise(partner = first(partner),
            categories = paste(unique(category_site), collapse = "; "),
            source = paste(unique(source), collapse = " + "),
            .groups = "drop") |>
  select(-key)

# ---- 2. ROR matching ------------------------------------------------------------------

ror_path <- here("data", "raw", "ror_partners_cache.csv")
ror_cache <- if (file.exists(ror_path)) read_csv(ror_path, show_col_types = FALSE, col_types = cols(.default = "c")) else
  tibble(partner = character(), ror = character(), ror_name = character(), ror_types = character(),
         country = character(), state = character(), city = character())

ror_lookup <- function(org) {
  resp <- request("https://api.ror.org/v2/organizations") |> req_url_query(affiliation = org) |>
    req_retry(max_tries = 3) |> req_perform() |> resp_body_json(simplifyVector = FALSE)
  hit <- keep(resp$items, \(it) isTRUE(it$chosen))
  if (!length(hit)) return(tibble(partner = org, ror = NA_character_))
  o   <- hit[[1]]$organization
  loc <- o$locations[[1]]$geonames_details %||% list()
  tibble(partner = org, ror = o$id,
         ror_name  = keep(o$names, \(n) "ror_display" %in% unlist(n$types))[[1]]$value,
         ror_types = paste(unlist(o$types), collapse = "; "),
         country   = loc$country_code %||% NA_character_,
         state     = loc$country_subdivision_name %||% NA_character_,
         city      = loc$name %||% NA_character_)
}

# manual ROR ids (aliases table) are fetched by id instead of affiliation matching
ror_by_id <- function(org, id) {
  o <- request(paste0("https://api.ror.org/v2/organizations/", basename(id))) |> req_perform() |>
    resp_body_json(simplifyVector = FALSE)
  loc <- o$locations[[1]]$geonames_details %||% list()
  tibble(partner = org, ror = o$id,
         ror_name  = keep(o$names, \(n) "ror_display" %in% unlist(n$types))[[1]]$value,
         ror_types = paste(unlist(o$types), collapse = "; "), country = loc$country_code %||% NA_character_,
         state = loc$country_subdivision_name %||% NA_character_, city = loc$name %||% NA_character_)
}
manual_ids <- aliases |> filter(!is.na(ror_override)) |> distinct(partner_canonical, ror_override)
manual_new <- manual_ids |> filter(!partner_canonical %in% ror_cache$partner)
if (nrow(manual_new)) {
  ror_cache <- bind_rows(ror_cache, pmap_dfr(manual_new, \(partner_canonical, ror_override)
    ror_by_id(partner_canonical, ror_override)) |> mutate(across(everything(), as.character)))
  write_csv(ror_cache, ror_path)
}
# a manual id replaces an earlier affiliation match for the same name
ror_cache <- ror_cache |>
  filter(!(partner %in% manual_ids$partner_canonical & !ror %in% manual_ids$ror_override))

todo <- setdiff(unique(partners$partner), ror_cache$partner)
if (length(todo)) {
  message(sprintf("ROR lookups: %d", length(todo)))
  new <- map_dfr(todo, \(p) { Sys.sleep(0.1); ror_lookup(p) })
  ror_cache <- bind_rows(ror_cache, mutate(new, across(everything(), as.character)))
  write_csv(ror_cache, ror_path)
}
# ROR "chosen" is not enough on its own for companies and local organisations: "Western CAM" was
# matched to "Western General Hospital". Accept a match only if the names share most of their words.
name_tokens <- function(x) {
  t <- str_to_lower(stringi::stri_trans_general(coalesce(x, ""), "Latin-ASCII")) |>
    str_remove_all("\\([^)]*\\)") |> str_replace_all("\\bst\\b", "saint") |>
    str_replace_all("[^a-z0-9 ]", " ") |> str_squish() |> str_split(" ")
  map(t, \(w) setdiff(w, c("of", "the", "at", "and", "for", "inc", "llc", "corporation", "company", "co", "ltd", "")))
}
generic <- c("university", "state", "college", "institute", "technology", "national", "laboratory", "lab",
             "research", "center", "centre", "community", "school", "department", "system", "united", "states")
# share of words in common, and whether the distinctive (non-generic) words overlap:
# "Kent State University" vs "Batken State University" shares 2 of 3 words but no distinctive word
name_sim <- function(a, b) map2_dbl(name_tokens(a), name_tokens(b), \(x, y) {
  if (!length(x) || !length(y)) return(0)
  dx <- setdiff(x, generic); dy <- setdiff(y, generic)
  if (length(dx) && length(dy) && !length(intersect(dx, dy))) return(0)
  length(intersect(x, y)) / max(length(x), length(y))
})
foreign_ok <- "australia|chile|canada|ukrain|sydney|rio tinto|glencore|scandinavian|evolution mining|northern star"

partners <- partners |>
  left_join(ror_cache, by = "partner") |>
  mutate(ror_sim = name_sim(partner, ror_name),
         ror_ok  = !is.na(ror) & ror_sim >= 0.6 &
                   (country %in% "US" | str_detect(str_to_lower(partner), foreign_ok)),
         ror_rejected = if_else(!is.na(ror) & !ror_ok, paste0(ror_name, " (", country, ")"), NA_character_),
         across(c(ror, ror_name, ror_types, country, state, city), \(x) if_else(ror_ok, x, NA_character_))) |>
  select(-ror_ok)

# ---- 3. Organisation class and knowledge producer ---------------------------------------

lc <- function(x) str_to_lower(coalesce(x, ""))

partners <- partners |>
  mutate(
    p = lc(partner), cat = lc(categories), rt = lc(ror_types),
    org_class = case_when(
      str_detect(p, "osage university partners") ~ "investor",
      str_detect(p, "research foundation") ~ "intermediary",            # university tech transfer / foundations
      str_detect(p, "school district|high school|boces|public schools|science and math academy|girl scouts|uprep|norman howard") ~ "k12_education",
      str_detect(p, "community college|\\bcc\\b|technical college|state college\\b|\\bctcs\\b|potomac state|parkersburg|metropolitan community|jccc|dmacc|stark state|lakeland|cuyahoga community|monroe community|finger lakes community|chemeketa|corning community") ~ "community_college",
      str_detect(p, "national lab|nat'l lab|\\blawrence livermore\\b|\\bpnnl\\b|\\bnetl\\b|\\bnrel\\b|\\bnlr\\b|laboratory for laser|nasa glenn|argonne|ames national|los alamos|idaho national|national security campus|national laboratory") ~ "national_lab",
      str_detect(rt, "education") | str_detect(p, "university|institute of technology|school of mines|\\bucla\\b|hajim|ntid|center for extended reality|geophysical institute") ~ "university",
      str_detect(rt, "facility") | str_detect(p, "research institute|hudsonalpha|woods hole|\\berc\\b|-erc|remade|research center|rti international|mri global|epri|sea grant|critical materials innovation hub|gulf of maine research") ~ "research_institute",
      str_detect(rt, "healthcare") ~ "healthcare",
      str_detect(p, "capital|venture|angels|\\bfund\\b|seed fund|invest|bank|equity|osage university partners|sosv|gener8tor|cantos|hamilton clark|kinterra|webster|western alliance|permanent equity") |
        str_detect(cat, "capital|venture") ~ "investor",
      str_detect(p, "foundation|benedum") | str_detect(cat, "philanthrop") ~ "philanthropy",
      str_detect(rt, "government") | str_detect(p, "^city of|county|state of|department|governor|legislature|commission|darpa|nswc|devcom|usaf|dla |geological survey|u\\.s\\.|state government|commonwealth|office of energy|division of geological|council of governments|intergovernmental") |
        str_detect(cat, "government|federal|state of alaska") ~ "government",
      str_detect(p, "chamber|partnership|council|alliance|association|assoc\\b|network|incubator|accelerator|hub\\b|enterprise|innovators|cluster|works\\b|jobsohio|team ?neo|magnet|lake to river|consortium|innovation district|source ?link|startup|i-?corps|teampennsylvania|team pennsylvania|catalyst connection|innovation works|launch|mep\\b|manufacturing extension|corp$|innovationcorp|ecosystem|meetup|stem|museum|science center|nexus|kc rising|great jobs|workforce|employment|goodwill|urban league|hispanic center|conxusneo|coalfield|jobs and hope|partner 4 work|community services|mattie rhodes|julius|connected communities|one roc|compass evaluation|education success") |
        str_detect(cat, "economic development|non-?profit|community|workforce|commercialization|service providers") ~ "intermediary",
      str_detect(rt, "company|nonprofit") | str_detect(cat, "industry|siting|team member") ~ "company",
      TRUE ~ "company"
    ),
    knowledge_producer = case_when(
      org_class %in% c("university", "national_lab", "research_institute", "healthcare") ~ "yes",
      org_class == "company" ~ "candidate",
      TRUE ~ "no"
    )
  ) |>
  select(-p, -cat, -rt)

# ---- 3b. Fallback: knowledge producers without a ROR match -> OpenAlex institution search -----
# (US institutions only, same name-similarity rule; one search costs $0.001)

fb_path <- here("data", "raw", "openalex_institution_search_cache.csv")
fb_cache <- if (file.exists(fb_path)) read_csv(fb_path, show_col_types = FALSE, col_types = cols(.default = "c")) else
  tibble(partner = character(), fb_ror = character(), fb_name = character())

need_fb <- partners |> filter(knowledge_producer == "yes", is.na(ror)) |> pull(partner) |> unique() |>
  setdiff(fb_cache$partner)
if (length(need_fb)) {
  new <- map_dfr(need_fb, \(p) {
    req <- request("https://api.openalex.org/institutions") |>
      req_url_query(search = str_remove_all(p, "[(),]"), filter = "country_code:US", `per-page` = 5,
                    select = "id,ror,display_name")
    if (nzchar(api_key)) req <- req_url_query(req, api_key = api_key)
    res <- req |> req_retry(max_tries = 3) |> req_perform() |> resp_body_json(simplifyVector = FALSE)
    hits <- res$results
    sims <- map_dbl(hits, \(h) name_sim(p, h$display_name))
    if (!length(hits) || max(sims) < 0.6) return(tibble(partner = p, fb_ror = NA_character_, fb_name = NA_character_))
    h <- hits[[which.max(sims)]]
    tibble(partner = p, fb_ror = h$ror %||% NA_character_, fb_name = h$display_name)
  })
  fb_cache <- bind_rows(fb_cache, new)
  write_csv(fb_cache, fb_path)
}
partners <- partners |>
  left_join(fb_cache, by = "partner") |>
  mutate(ror_source = case_when(!is.na(ror) ~ "ROR affiliation", !is.na(fb_ror) ~ "OpenAlex search", TRUE ~ NA_character_),
         ror_name = coalesce(ror_name, fb_name), ror = coalesce(ror, fb_ror)) |>
  select(-fb_ror, -fb_name)

# ---- 4. OpenAlex institutions for ROR-matched knowledge producers -------------------------

oa_path <- here("data", "raw", "openalex_institutions.json")
oa_cache <- if (file.exists(oa_path)) read_json(oa_path, simplifyVector = FALSE) else list()
have <- map_chr(oa_cache, \(i) i$ror %||% "")

rors <- partners |> filter(!is.na(ror), knowledge_producer == "yes") |> pull(ror) |> unique() |> setdiff(have)
if (length(rors)) {
  batches <- split(rors, ceiling(seq_along(rors) / 50))
  for (b in batches) {
    req <- request("https://api.openalex.org/institutions") |>
      req_url_query(filter = paste0("ror:", paste(b, collapse = "|")), `per-page` = 100,
                    select = "id,ror,display_name,type,works_count,cited_by_count,counts_by_year,geo")
    if (nzchar(api_key)) req <- req_url_query(req, api_key = api_key)
    res <- req |> req_retry(max_tries = 3) |> req_perform() |> resp_body_json(simplifyVector = FALSE)
    oa_cache <- c(oa_cache, res$results)
  }
  write_json(oa_cache, oa_path, auto_unbox = TRUE)
}

window_year <- as.integer(format(min(engines$window_from), "%Y"))
oa_inst <- map_dfr(oa_cache, \(i) tibble(
  ror = i$ror, oa_institution = str_remove(i$id, "https://openalex.org/"), oa_type = i$type,
  oa_works_total = i$works_count,
  oa_works_5y = sum(map_int(i$counts_by_year %||% list(), \(y) if (y$year >= window_year) as.integer(y$works_count) else 0L))
)) |> distinct(ror, .keep_all = TRUE)

partners <- partners |>
  left_join(oa_inst, by = "ror") |>
  # institution-level counts above this are implausible for one organisation (OpenAlex lineage errors)
  mutate(oa_outlier = coalesce(oa_works_5y, 0) > 200000) |>
  left_join(read_csv(here("data", "manual", "partner_sources.csv"), show_col_types = FALSE) |>
              select(engine_name, partners_url, completeness), by = "engine_name") |>
  arrange(engine_name, factor(knowledge_producer, c("yes", "candidate", "no")), desc(oa_works_5y), partner)

write_csv(partners, here("data", "processed", "partners.csv"))

# ---- Report ----------------------------------------------------------------------------------

message(sprintf("Partners (partner x Engine): %d; ROR-matched: %d", nrow(partners), sum(!is.na(partners$ror))))
partners |> count(engine_name, knowledge_producer) |>
  pivot_wider(names_from = knowledge_producer, values_from = n, values_fill = 0) |> print(n = Inf)
partners |> count(org_class, sort = TRUE) |> print()
