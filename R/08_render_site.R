# Step 8. Render the per-Engine reports, the pipeline, methodology, publications, patents, comparison and index
# pages into docs/ (GitHub Pages)
#
# One copy of the data pages per technology profile version (R/profile.R): v1 in docs/, v3.1 in docs/v3/.
# Data pages (12 Engines, index, publications, patents) read the files of their version; pipeline, analysis,
# methodology and the comparison of versions are rendered once, in docs/. The header switches versions.
#
# Usage: Rscript R/08_render_site.R                       all versions, all Engines
#        ONLY_ENGINE=NEO-SMART Rscript R/08_render_site.R
#        ONLY_VERSION=v3_1 Rscript R/08_render_site.R      data pages of one version only (and no shared pages)

library(rmarkdown)
library(readr)
library(stringr)
library(here)
source(here("R", "profile.R"))

slug <- \(x) str_replace_all(str_to_lower(x), "[^a-z0-9]+", "-")

engines <- read_csv(here("data", "processed", "engines.csv"), show_col_types = FALSE)$engine_name
only <- Sys.getenv("ONLY_ENGINE")
if (nzchar(only)) engines <- intersect(engines, only)
versions <- PROFILE_VERSIONS
only_v <- Sys.getenv("ONLY_VERSION")
if (nzchar(only_v)) versions <- intersect(versions, only_v)

render_page <- function(rmd, out_file, out_dir, params = NULL) {
  render(here("reports", rmd), params = params, output_file = out_file, output_dir = out_dir,
         intermediates_dir = tempdir(), envir = new.env(), quiet = TRUE)
}

for (v in versions) {
  Sys.setenv(PROFILE_VERSION = v)
  out_dir <- if (nzchar(PROFILE_SITE_DIR[[v]])) here("docs", PROFILE_SITE_DIR[[v]]) else here("docs")
  dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
  for (e in engines) {
    message("Rendering ", e, " (profile ", v, ")")
    render_page("engine_report.Rmd", paste0(slug(e), ".html"), out_dir, params = list(engine = e))
  }
  for (page in c("publications", "patents", "index")) {
    message("Rendering ", page, " (profile ", v, ")")
    render_page(paste0(page, ".Rmd"), paste0(page, ".html"), out_dir)
  }
}
Sys.setenv(PROFILE_VERSION = "v1")
if (!nzchar(only_v)) for (page in c("pipeline", "analysis", "methodology", "neighbours", "compare")) {
  message("Rendering ", page)
  render_page(paste0(page, ".Rmd"), paste0(page, ".html"), here("docs"))
}
file.create(here("docs", ".nojekyll"))
message("Site written to ", here("docs"))
