# Minimal-plus prompt: the technologies of an NSF Engine grant

Version: minimal-plus-1 (2026-11-17). The minimal prompt (py/prompts/grant_technologies_minimal.md) with two
sentences added after its first test: one on the size of a technology (the minimal prompt split some grants
into 8-11 one-phrase technologies, and the number changed from run to run) and one on broad fields
("advanced manufacturing", "biotechnology" became technologies of their own). Nothing else is added.
Input as for the other prompts: the 12 grants split into numbered sentences (data/processed/tech_v2_sentences.csv).

---

Below are the titles and abstracts of 12 NSF Regional Innovation Engine grants, split into numbered
sentences. Each Engine is a regional programme built around some science and technology.

For each Engine, find what science and technology it works on. Copy out the phrases of the grant that name
it, word for word, and group them into the Engine's technologies. Give each technology a short label.

An Engine usually has 2 to 5 technologies: put together the phrases that one journal or one patent examiner
would handle. Do not make a technology of a broad field name alone (such as "advanced manufacturing") when
the grant names nothing specific in it.

Return CSV with the header `engine_name,sent_id,fragment,tech_id,tech_label`, every text field in double
quotes, one row per phrase. `fragment` is copied exactly from sentence `sent_id`; `tech_id` numbers the
technologies of each Engine 1, 2, 3, ... No other text.
