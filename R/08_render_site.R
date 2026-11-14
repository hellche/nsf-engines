# Step 8. Render the per-Engine reports, the pipeline, methodology, publications, patents and index pages into docs/ (GitHub Pages)
#
# Usage: Rscript R/08_render_site.R            all Engines
#        ONLY_ENGINE=NEO-SMART Rscript R/08_render_site.R

library(rmarkdown)
library(readr)
library(stringr)
library(here)

out_dir <- here("docs")
dir.create(out_dir, showWarnings = FALSE)
slug <- \(x) str_replace_all(str_to_lower(x), "[^a-z0-9]+", "-")

engines <- read_csv(here("data", "processed", "engines.csv"), show_col_types = FALSE)$engine_name
only <- Sys.getenv("ONLY_ENGINE")
if (nzchar(only)) engines <- intersect(engines, only)

for (e in engines) {
  message("Rendering ", e)
  render(here("reports", "engine_report.Rmd"), params = list(engine = e),
         output_file = paste0(slug(e), ".html"), output_dir = out_dir,
         intermediates_dir = tempdir(), envir = new.env(), quiet = TRUE)
}
for (page in c("pipeline", "methodology", "publications", "patents", "index")) {
  message("Rendering ", page)
  render(here("reports", paste0(page, ".Rmd")), output_file = paste0(page, ".html"), output_dir = out_dir,
         intermediates_dir = tempdir(), envir = new.env(), quiet = TRUE)
}
file.create(file.path(out_dir, ".nojekyll"))
message("Site written to ", out_dir)
