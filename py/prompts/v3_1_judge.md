# v3.1 judge prompt: does a candidate topic or CPC group describe one technology of an NSF Engine grant?

Version: v3.1-judge (2026-11-15). Used by step 5 v3.1 only for the technologies that the rank fusion
(py/05v3_1b_fuse.py) could not confirm: no candidate with confirmation "high" for that kind of item
(OpenAlex topics or CPC main groups). Input per technology: its label and its verbatim fragments from the
grant (data/processed/tech_v3_1_fragments.csv) and the top JUDGE_TOP candidates by fused rank
(data/processed/tech_v3_1_fused_{oa,cpc}.csv.gz), each with its title (topics: name and subfield;
CPC: subclass title and group title). Output: one score per candidate.

Runs so far: one run, 2026-11-15, done by hand in a Claude Code chat session (not through the API: no
Anthropic API key in the project), saved as data/manual/tech_v3_1_judge_raw.csv: 22 technologies
(6 for topics, 16 for CPC) x 12 candidates = 264 scores. This run is **not reproducible**: there is no
script that sends the prompt, and the model in the chat also had the whole conversation as context
(including the fusion results and the earlier review), not only this prompt and the candidates. The
candidate lists were printed from tech_v3_1_fused_*.csv.gz (top 12 by rank_fused) for the technologies
without a "high" candidate. The judge can only score the candidates it is given: where the right item is
not among the 12 (e.g. C08L/C08H for BRIDGES biobased manufacturing, A61F2 for IMPACT orthopedic devices),
the technology stays without a core item.

---

You are given one technology of an NSF Regional Innovation Engine grant, described by a short label and the
exact phrases of the grant that name it, and a list of candidate classification items: OpenAlex research
topics or CPC patent groups. For each candidate, judge whether research papers in that topic, or patents
in that CPC group, would be **about this technology as the grant describes it**.

Score each candidate:
- **3** — directly about the technology: a typical paper or patent in this item is work on what the grant
  phrases name (e.g. "laser component and system manufacturing" → H01S5 Semiconductor lasers).
- **2** — clearly part of the technology but narrower or one step removed: a component, a main method or a
  main application named in the grant phrases (e.g. "cold chain technologies" → F25D Refrigerators).
- **1** — shares words or a general area, but a typical paper or patent in it would not be about this
  technology (e.g. "musculoskeletal injury or disease" → F16B Devices for securing together).
- **0** — unrelated, or related only through a word with another meaning (e.g. "digital twins" →
  Twin Pregnancy).

Rules:
1. Judge against the grant phrases, not against what the Engine might also do: use only the label and the
   fragments given, plus general knowledge of what papers in a topic or patents in a CPC group are about.
2. Judge each candidate on its own: several candidates may get 3, or none.
3. A generic item that would hold any technology (e.g. "Diverse Industrial Engineering", "Economic and
   Industrial Development") gets at most 1.
4. Give a reason of a few words for every score.

Return CSV with the header `kind,engine_name,tech_id,item_id,score,reason`, one row per candidate.
No other text.
