# v3.1 simple, judge prompt: does a candidate topic or CPC group describe one technology of an NSF Engine grant?

Version: v3.1s-judge-1 (2026-11-17). Step 3 of the simple v3.1 profile. The rubric (part after `---`) is the
v3.1 judge rubric (py/prompts/v3_1_judge.md) unchanged; only the input changed: for EVERY one of the 43 common
technologies (data/processed/tech_minplus_technologies.csv), the 50 OpenAlex topics and the 50 CPC main groups
closest to the technology by embedding (py/05v3_1s_simple.py, data/processed/tech_v3_1s_rank_{oa,cpc}.csv.gz,
rank <= 50). Each candidate is shown with its title (topics: name and subfield; CPC: subclass title and group
title). One file per technology (`candidates/<file>.txt`); the model writes one CSV per technology.

Three independent runs, each split in two halves by Engine (separate model sessions in a chat, as subagents,
not through the API: not reproducible as such; the prompt and the candidate files are). Consensus:
py/05v3_1s_judge_consensus.py.

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
