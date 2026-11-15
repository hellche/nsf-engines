# Reference lists

Downloaded by `py/00_reference_lists.py` on 2026-11-15.

| File | Source | Rows |
|---|---|---|
| `cpc_titles_202608.csv.gz` | CPC title list, scheme 2026.08: https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCTitleList202608.zip (bulk page: https://www.cooperativepatentclassification.org/cpcSchemeAndDefinitions/bulk) | 254314 codes, 9867 main groups |
| `openalex_topics.csv` | OpenAlex topics API: https://api.openalex.org/topics (docs: https://docs.openalex.org/api-entities/topics) | 4516 topics |

Versions: the CPC site labels the title list "CPC Title List (2026.08)" (files dated 2026-08-01).
OpenAlex gives its topic list no version number; `created_date` of the topics in the API is January 2024;
`updated_date` changes daily with the work counts.

`dots` in the CPC file is the depth of a subgroup under its main group (empty for sections, classes
and subclasses, 0 for main groups). Titles are as published, including {curly} markers and references.
