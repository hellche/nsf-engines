# Prompt v3.2: the technologies of an NSF Engine grant (verbatim fragments, grouped)

Version: v3.2 (2026-11-17). The common first step of the technology profile: its output, the grant's
technologies, is the input of every profile version that chooses topics and CPC groups (v1, v3.1).
Changes from v3.1 (py/prompts/v3_1_extract_technical.md, kept unchanged): explicit rules for the grey zones
that v3.1 left to judgement (products vs industries, applications, cross-cutting methods); one prompt for all
12 grants in one run; the Engine's name is given so that it can be left out.

Input: for each of the 12 Engines, the grant title and the abstract split into numbered sentences
(sentence 0 is the title; data/processed/tech_v2_sentences.csv, column `text_original`).
Output: one row per fragment. Each run is checked by script (every fragment must be a verbatim substring of
its sentence; the label must use only words of its fragments) and three independent runs are compared for
stability.

---

You are given the titles and abstracts of NSF Regional Innovation Engine awards, each split into numbered
sentences. For each Engine, do two things: (A) copy out, word for word, only the parts that name **science or
technology**; (B) group these fragments into the grant's technologies.

## A. Fragments

Extract a fragment when it names any of:
- a material, substance, organism or natural resource that is studied, produced or processed
  (e.g. "perennial grasses such as miscanthus and switchgrass", "critical minerals", "polymers");
- a technology, device, product or system (e.g. "semiconductor lasers", "smart grid", "quantum sensors");
- a scientific or engineering process or method (e.g. "biomanufacturing", "recycling of plastics",
  "life cycle assessment");
- a scientific field or technical area (e.g. "precision optics and imaging", "musculoskeletal health").

Do not extract:
- the region, states, counties, cities, the Engine's name or acronym, NSF and its programmes;
- economic development, jobs, workforce, education and training, entrepreneurship, investment, funding;
- partnerships, coalitions, stakeholders, governance, community engagement, equity;
- national security, supply chains, competitiveness or leadership, unless the same words name a technology;
- general aims such as "innovation", "commercialization", "translation", "growth", "scale-up" on its own;
- generic qualities and goals ("resilience", "reliability", "efficiency", "sustainability", "security",
  "affordability") when they stand without a technical object. Keep the object: from "a resilient and
  efficient power grid" extract "power grid".

Grey zones (apply these rules):
1. **Products vs industries.** Extract what the Engine itself makes, studies or processes, even when it is a
   product category ("vaccines", "food and feed ingredients", "biobased products"). Do not extract markets or
   sectors that use the Engine's output ("the automotive, construction materials, and packaging sectors",
   "aerospace, defense", "pharmaceuticals, finance and insurance", "healthcare").
2. **Applications.** Do not extract an application when the technology itself is named elsewhere in the grant
   ("lasers ... for medical diagnostics and vision care": extract the lasers, not "medical diagnostics").
   Extract an application only when the grant names no technology for it except the application itself.
3. **Cross-cutting methods** (AI, machine learning, digital twins, data analytics, sensors). Extract them.
   In part B they form a technology of their own only when the grant presents them as a separate line of work;
   otherwise they go with the technology they are applied to in that sentence.

Rules:
1. Copy fragments **verbatim**: the exact characters of the sentence, no paraphrase, no added words, no
   corrected spelling. A fragment is a contiguous span of one sentence.
2. Keep a fragment as short as possible while still meaningful on its own: a noun phrase or a clause, not the
   whole sentence when only part of it is technical.
3. A fragment must not contain the words "Engine" or "Engines" or the Engine's name; shorten it to leave
   them out.
4. A sentence may give zero, one or several fragments. Most programme sentences give none.
5. Do not add anything from your own knowledge: if the text does not name it, it is not extracted.
6. Extract each technical idea where it is stated most specifically; repeat it only if a later sentence adds
   something (a new material, method or product).

## B. Technologies

For each Engine, group its fragments into the grant's distinct technologies: the separate lines of science
and technology the Engine works on (usually 2-5). Two fragments belong to the same technology when one
patent examiner or one journal would handle both. Every fragment gets exactly one technology.

- `tech_id`: 1, 2, 3, ... per Engine, in order of first appearance in the text.
- `tech_label`: a short label of 2-6 words **made only of words that appear in the fragments of that
  technology**. No words from your own knowledge.
- Do not make a technology for the Engine's general purpose (e.g. "economic growth"): such fragments are not
  extracted at all (part A).

## Output

Return CSV with the header `engine_name,sent_id,fragment,tech_id,tech_label`, every text field in double
quotes (a double quote inside a field is written twice), one row per fragment, Engines in the order given,
fragments in the order of the sentences. `engine_name` exactly as given in the input. No other text.
