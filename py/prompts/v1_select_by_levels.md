# Prompt v1 (by levels): a language model picks OpenAlex topics and CPC groups for each technology

Version: v1-levels-1 (2026-11-17). Profile version 1, rebuilt on the common technologies of the grants
(data/processed/tech_minplus_technologies.csv, prompt grant_technologies_minimal_plus.md). The model chooses
from the full classifications, but level by level, as an examiner would: first a short list of CPC
subclasses (652) or OpenAlex subfields (250), then only the groups or topics inside the ones it chose.
The files it reads are made from data/reference/ (CPC Title List 2026.08 without indexing groups 2000+ and
99/00, as in v3.1; OpenAlex topics with keywords). Three independent runs; consensus = items chosen by at
least two runs.

---

You are given 43 technologies of 12 NSF Regional Innovation Engine grants (file `technologies.txt`: each
technology has a label and the phrases of the grant that name it). For each technology, choose the
OpenAlex topics and the CPC main groups where research papers and patents about this technology would be
classified. Use your knowledge of the fields.

Work level by level:
- CPC: read `cpc_subclasses.txt`, choose up to 2 subclasses for the technology, then read the files
  `cpc_groups/<subclass>.txt` of those subclasses and choose up to 2 main groups in total.
- OpenAlex: read `oa_subfields.txt`, choose up to 2 subfields, then read the files `oa_topics/<file name>.txt`
  of those subfields and choose up to 2 topics in total.

Choose only codes and topic ids that appear in these files. If nothing fits, choose fewer.

Return CSV with the header `engine_name,tech_id,kind,item_id,item_title,via`, every text field in double
quotes, one row per chosen item: `kind` is `cpc` or `oa`; `item_id` is the CPC main group (e.g. C22B3/00)
or the topic id (e.g. T10001); `item_title` its title as in the file; `via` the subclass or the subfield
file name it was chosen through. No other text.
