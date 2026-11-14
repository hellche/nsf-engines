# v3.1 prompt: extract the science and technology content of an NSF Engine grant, grouped by technology

Version: v3.1 (2026-11-14). Used by step 5 v3.1 (technology profile from extracted fragments).
Changes from v3.0 (py/prompts/v3_extract_technical.md, kept unchanged):
- industries and sectors of application, and generic qualities ("resilience", "efficiency") without a
  technical object, are no longer extracted (they pulled rankings towards regional-development topics and
  unrelated CPC groups);
- the words "Engine"/"Engines" are kept out of fragments (PatentSBERTa reads them as motors);
- every fragment is assigned to one of the grant's technologies, so that the profile can be chosen
  technology by technology instead of from one overall ranking.
Input: the grant title and the abstract split into numbered sentences (data/processed/tech_v2_sentences.csv,
column `text_original`; sentence 0 is the title). Output: one row per extracted fragment.

---

You are given the title and the abstract of one NSF Regional Innovation Engine award, split into numbered
sentences. Your task has two parts: (A) copy out, word for word, only the parts that name **science or
technology**; (B) group these fragments into the grant's technologies.

## A. Fragments

Extract a fragment when it names any of:
- a material, substance, organism or natural resource being studied, produced or processed
  (e.g. "perennial grasses such as miscanthus and switchgrass", "critical minerals", "polymers");
- a technology, device, product or system (e.g. "semiconductor lasers", "smart grid", "quantum sensors");
- a scientific or engineering process or method (e.g. "biomanufacturing", "recycling of plastics",
  "life cycle assessment", "AI/ML methods that accelerate materials design");
- a scientific field or technical area (e.g. "precision optics and imaging", "musculoskeletal health").

Do not extract:
- the region, states, cities, the Engine's name or acronym, the NSF programme;
- economic development, jobs, workforce, education and training, entrepreneurship, investment;
- partnerships, coalitions, stakeholders, governance, community engagement, equity;
- national security, supply chains, competitiveness or leadership, unless the same words name a technology;
- general aims such as "innovation", "commercialization", "translation", "growth";
- **industries, sectors and markets of application** (e.g. "automotive, construction materials, and
  packaging sectors", "aerospace, defense", "pharmaceuticals, finance and insurance", "healthcare"),
  unless the same words name a material, product or technology made by the Engine;
- **generic qualities and goals** (e.g. "resilience", "reliability", "efficiency", "sustainability",
  "security", "affordability") when they stand without a technical object. Keep the technical object:
  from "a resilient and efficient power grid" extract "power grid".

Rules:
1. Copy fragments **verbatim**: the exact characters of the sentence, no paraphrase, no added words,
   no corrected spelling. A fragment is a contiguous span of one sentence.
2. Keep a fragment as short as possible while still meaningful on its own: a noun phrase or a clause,
   not the whole sentence when only part of it is technical.
3. A fragment must not contain the words "Engine" or "Engines"; shorten it to leave them out.
4. A sentence may give zero, one or several fragments. Most programme sentences give none.
5. Do not add anything from your own knowledge: if the text does not name it, it is not extracted.
6. Extract each technical idea where it is stated most specifically; repeat it only if a later sentence
   adds something (a new material, method or product).

## B. Technologies

Group the fragments into the grant's distinct technologies: the separate lines of science and technology
the Engine works on (usually 2-5). Two fragments belong to the same technology when one patent examiner or
one journal would handle both. Every fragment gets exactly one technology.

- `tech_id`: 1, 2, 3, ... in order of first appearance in the text.
- `tech_label`: a short label of 2-6 words **made only of words that appear in the fragments of that
  technology** (e.g. "lithium-ion battery recycling", "semiconductor lasers"). No words from your own knowledge.
- Do not make a technology for the Engine's general purpose (e.g. "economic growth"): such fragments are
  not extracted at all (part A).
- A fragment naming a cross-cutting method (e.g. "AI", "digital twins") goes with the technology it is
  applied to in that sentence; it gets its own technology only if the text presents it as a line of work
  of its own.

Return CSV with the header `sent_id,fragment,tech_id,tech_label` (fragment and tech_label in double quotes),
one row per fragment, in the order of the sentences. No other text.
