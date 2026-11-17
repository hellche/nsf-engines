# Minimal prompt: the technologies of an NSF Engine grant

Version: minimal-1 (2026-11-17). An experiment against prompt v3.2 (py/prompts/grant_technologies_v3_2.md):
only the idea of the task, with no lists of what to take or leave, no examples and no rules for grey zones.
Kept only what the output check needs: fragments are copied word for word, and a fixed output format.
Input as for v3.2: the 12 grants split into numbered sentences (data/processed/tech_v2_sentences.csv).

---

Below are the titles and abstracts of 12 NSF Regional Innovation Engine grants, split into numbered
sentences. Each Engine is a regional programme built around some science and technology.

For each Engine, find what science and technology it works on. Copy out the phrases of the grant that name
it, word for word, and group them into the Engine's technologies. Give each technology a short label.

Return CSV with the header `engine_name,sent_id,fragment,tech_id,tech_label`, every text field in double
quotes, one row per phrase. `fragment` is copied exactly from sentence `sent_id`; `tech_id` numbers the
technologies of each Engine 1, 2, 3, ... No other text.
