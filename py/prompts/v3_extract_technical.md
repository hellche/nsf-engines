# v3 prompt: extract the science and technology content of an NSF Engine grant

Version: v3.0 (2026-11-14). Used by step 5 v3 (technology profile from extracted fragments).
Input: the grant title and the abstract split into numbered sentences (data/processed/tech_v2_sentences.csv,
column `text_original`; sentence 0 is the title). Output: one row per extracted fragment.

---

You are given the title and the abstract of one NSF Regional Innovation Engine award, split into numbered
sentences. Your task is to copy out, word for word, only the parts that name **science or technology**.

Extract a fragment when it names any of:
- a material, substance, organism or natural resource being studied, produced or processed
  (e.g. "perennial grasses such as miscanthus and switchgrass", "critical minerals", "polymers");
- a technology, device, product or system (e.g. "semiconductor lasers", "smart grid", "quantum sensors");
- a scientific or engineering process or method (e.g. "biomanufacturing", "recycling of plastics",
  "life cycle assessment", "AI/ML methods that accelerate materials design");
- a scientific field or application domain stated as a technical area (e.g. "precision optics and imaging",
  "musculoskeletal health").

Do not extract:
- the region, states, cities, the Engine's name or acronym, the NSF programme;
- economic development, jobs, workforce, education and training, entrepreneurship, investment;
- partnerships, coalitions, stakeholders, governance, community engagement, equity;
- national security, supply chains, competitiveness or leadership, unless the same words name a technology;
- general aims such as "innovation", "commercialization", "translation", "growth".

Rules:
1. Copy fragments **verbatim**: the exact characters of the sentence, no paraphrase, no added words,
   no corrected spelling. A fragment is a contiguous span of one sentence.
2. Keep a fragment as short as possible while still meaningful on its own: a noun phrase or a clause,
   not the whole sentence when only part of it is technical.
3. A sentence may give zero, one or several fragments. Most programme sentences give none.
4. Do not add anything from your own knowledge: if the text does not name it, it is not extracted.

Return CSV with the header `sent_id,fragment` (fragment in double quotes), one row per fragment,
in the order of the sentences. No other text.
