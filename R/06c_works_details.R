# Step 6c. Authors and venue (journal, conference, repository) of the people's works, for APA-style references
#
# Looks up the works already listed in step 6a by their OpenAlex id, so the lists themselves do not change.
#
# Input:  data/processed/works_people.csv
# Output: data/raw/openalex_works/details_people.json   cached API results (delete to refresh)
#         data/processed/works_details.csv              one row per work: authors (APA style), author names and ids, venue
#
# Cost: one request per 50 works, about 20 requests ($0.002).

library(httr2)
library(jsonlite)
library(dplyr)
library(stringr)
library(purrr)
library(readr)
library(here)

api_key   <- Sys.getenv("OPENALEX_API_KEY")
works     <- read_csv(here("data", "processed", "works_people.csv"), show_col_types = FALSE)
cache     <- here("data", "raw", "openalex_works", "details_people.json")
max_names <- 20  # APA 7: up to 20 authors; beyond that the first 19, "...", the last

ids <- unique(works$work_id)
raw <- if (file.exists(cache)) read_json(cache, simplifyVector = FALSE) else list()
todo <- setdiff(ids, map_chr(raw, \(w) str_remove(w$id, "https://openalex.org/")))
for (chunk in split(todo, ceiling(seq_along(todo) / 50))) {
  req <- request("https://api.openalex.org/works") |>
    req_url_query(filter = paste0("openalex_id:", paste(chunk, collapse = "|")), `per-page` = 50,
                  select = "id,authorships,primary_location") |>
    req_retry(max_tries = 30, is_transient = \(r) resp_status(r) %in% c(429, 503), backoff = \(i) 20)
  if (nzchar(api_key)) req <- req_url_query(req, api_key = api_key)
  raw <- c(raw, resp_body_json(req_perform(req), simplifyVector = FALSE)$results)
}
write_json(raw, cache, auto_unbox = TRUE)

# "Stefan F. Preble" -> "Preble, S. F."; a name without spaces is kept as it is
apa_name <- function(x) {
  parts <- str_split_1(str_squish(x), " ")
  if (length(parts) < 2) return(x)
  initials <- str_sub(str_remove_all(head(parts, -1), "[.]"), 1, 1)
  paste0(tail(parts, 1), ", ", paste0(initials, ".", collapse = " "))
}
# APA author list from names already in "Last, F." form; names may carry markup (e.g. bold)
apa_authors <- function(names) {
  n <- length(names)
  if (n == 0) return(NA_character_)
  if (n == 1) return(names)
  if (n > max_names) return(paste0(paste(names[1:(max_names - 1)], collapse = ", "), ", ... ", names[n]))
  paste0(paste(names[-n], collapse = ", "), ", & ", names[n])
}

# One string from a JSON field; missing values come back as "" (cached nulls are read as empty lists)
chr1 <- \(x) if (is.character(x) && length(x) == 1) x else ""

# author_names / author_ids: all authors in order, "; "-separated, so a report can mark one of them
details <- map_dfr(raw, function(w) {
  au    <- w$authorships %||% list()
  names <- map_chr(au, \(a) apa_name(chr1(a$author$display_name)))
  tibble(work_id      = str_remove(w$id, "https://openalex.org/"),
         authors      = apa_authors(names),
         author_names = paste(names, collapse = "; "),
         author_ids   = paste(map_chr(au, \(a) str_remove(chr1(a$author$id), "https://openalex.org/")), collapse = "; "),
         venue        = na_if(chr1(w$primary_location$source$display_name), ""))
}) |> distinct(work_id, .keep_all = TRUE)

write_csv(details, here("data", "processed", "works_details.csv"))
message(sprintf("Details for %d of %d works; with venue: %d", nrow(details), length(ids), sum(!is.na(details$venue))))
