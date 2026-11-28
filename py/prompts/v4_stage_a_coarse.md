# Profile v4, stage A: which CPC subclasses and OpenAlex subfields belong to a technology, wholly or in part

Version: v4-a-1 (2026-11-28). Profile v4 chooses codes top-down through the classifications, without a limit
on the number of items per technology, and records whether a coarse category belongs to the technology as a
whole or only in part. Input: the technologies of `data/manual/tech_v4_technologies.csv` (label, the exact
phrases of the 2026 grant and the full sentences they come from), the 652 CPC subclasses (scheme 2026.08)
and the 250 OpenAlex subfields (files made by `py/05v4a_inputs.py`). No embeddings: for broad technologies
("metals", "coatings") the grant gives one word, and geometry on one word brings noise.

Three independent runs (separate model sessions, as subagents in a chat, not through the API: the prompt and
the input files are reproducible, the answers are not). Consensus (`py/05v4c_consensus.py`): a category is
kept if at least 2 runs mark it; it is `whole` only if all 3 runs mark it `whole`, otherwise `part`
(decided 2026-11-28 after the first NEO-SMART runs: with "2 of 3" metal wire, needles, nails and chains entered
"metals" whole; a disputed category now goes to stage B, where the judge scores the groups inside).
Stage B (`v4_stage_b_fine.md`) scores the groups and topics inside every `part` category.

---

You are given the technologies of one NSF Regional Innovation Engine grant (`technologies.txt`: for each, a
short label, the exact phrases of the grant that name it, and the full grant sentences they come from), the
list of CPC patent subclasses (`cpc_subclasses.txt`) and the list of OpenAlex research subfields
(`oa_subfields.txt`).

For each technology, read the whole of both lists and mark every subclass and every subfield where patents
or research papers **about this technology as the grant describes it** are classified:

- **whole** — nearly every patent in this subclass, or nearly every paper in this subfield, is about the
  technology (e.g. "coatings" → C09D Coating compositions; "metals" → C22C Alloys).
- **part** — the category holds a clear, sizeable share of work on the technology, but also much that is not
  (e.g. "coatings" → C23C Coating metallic material, which also holds vapour deposition for electronics;
  "polymers" → B29C Shaping or joining of plastics).
- leave a category out if work on the technology would only appear there by accident, or through a word with
  another meaning.

Rules:
1. Judge against the grant's phrases and sentences, plus general knowledge of what patents in a CPC subclass
   or papers in an OpenAlex subfield are about. Do not add what the Engine might also do.
2. A technology may have many categories, or one. Do not stop at a fixed number. Mark every category that
   qualifies; the same category may belong to several technologies.
3. Prefer **part** when unsure between whole and part: stage B will then look inside.
4. Generic categories that would hold any technology (e.g. "General Engineering", "Industrial and
   Manufacturing Engineering" as a subfield, G06Q Business methods) are at most **part**, and only if the
   technology is mainly found there.
5. Give a reason of a few words for each mark.

Return CSV with the header `engine_name,tech_id,kind,code,title,mark,reason`, every text field in double
quotes, one row per marked category: `kind` is `cpc` or `oa`; `code` is the subclass (e.g. C09D) or the
subfield file name from `oa_subfields.txt`; `title` as in the list; `mark` is `whole` or `part`. No other text.
