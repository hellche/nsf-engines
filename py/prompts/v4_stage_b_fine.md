# Profile v4, stage B: score the CPC main groups and OpenAlex topics inside the categories marked `part`

Version: v4-b-1 (2026-11-28). For every technology, the candidates are (1) all main groups of each CPC
subclass and all topics of each OpenAlex subfield that stage A kept as `part`, and (2) every item the
earlier profiles chose for the matching technology (v1 by levels, v3.1 simple), so that nothing chosen
before is lost without a score. Categories kept as `whole` enter the profile entirely and are not scored.
Files: `py/05v4b_stage_b_inputs.py`. The rubric below is the v3.1 judge rubric (`v3_1s_judge.md`) with
rule 2 made explicit for the absence of a limit.

Three independent runs (subagents in a chat, not through the API). Consensus (`py/05v4c_consensus.py`): an
item enters the profile if it scores 2 or 3 in at least 2 of the 3 runs. No limit per technology.

---

You are given one technology of an NSF Regional Innovation Engine grant, described by a short label, the
exact phrases of the grant that name it and the full sentences they come from, and a list of candidate
classification items: OpenAlex research topics (with keywords) or CPC main groups (with their first-level
subgroups). For each candidate, judge whether research papers in that topic, or patents in that CPC group,
would be **about this technology as the grant describes it**.

Score each candidate:
- **3** — directly about the technology: a typical paper or patent in this item is work on what the grant
  phrases name (e.g. "coatings" → C09D5/00 Coating compositions characterised by their physical nature).
- **2** — clearly part of the technology but narrower or one step removed: a component, a main method, a
  main material or a main application of what the grant names (e.g. "metals" → B22D Casting of metals).
- **1** — shares words or a general area, but a typical paper or patent in it would not be about this
  technology (e.g. "polymers" → F16G Belts).
- **0** — unrelated, or related only through a word with another meaning (e.g. "metals" → Heavy metals in
  plants).

Rules:
1. Judge against the grant phrases and sentences, not against what the Engine might also do.
2. Judge each candidate on its own: any number of candidates may get 3, or none. There is no quota.
3. A generic item that would hold any technology gets at most 1.
4. Give a reason of a few words for every score.

Return CSV with the header `kind,engine_name,tech_id,item_id,score,reason`, one row per candidate.
No other text.
