"""Profile v4, stage A inputs: the files a language model reads to mark CPC subclasses and OpenAlex subfields.

The classification files are those of profile v1 by levels (py/05v1a_level_files.py: 652 CPC subclasses with
their main groups, 250 OpenAlex subfields with their topics), so that v1 and v4 see the same lists.
technologies.txt is rebuilt from data/manual/tech_v4_technologies.csv: label, the exact phrases of the 2026
grant and the full sentences they come from (one Engine per folder).

Run:  python3 py/05v4a_inputs.py <output folder> [engine_name ...]      (pandas only)
      default engine: NEO-SMART
Prompt: py/prompts/v4_stage_a_coarse.md
"""

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1])
ENGINES = sys.argv[2:] or ["NEO-SMART"]

subprocess.run([sys.executable, str(ROOT / "py" / "05v1a_level_files.py"), str(OUT)], check=True)

tech = pd.read_csv(ROOT / "data" / "manual" / "tech_v4_technologies.csv", dtype=str)
tech = tech[tech.engine_name.isin(ENGINES)]
if tech.empty:
    sys.exit(f"no technologies for {ENGINES} in data/manual/tech_v4_technologies.csv")
with open(OUT / "technologies.txt", "w", encoding="utf-8") as f:
    for _, r in tech.iterrows():
        f.write(f"engine_name: {r.engine_name} | tech_id: {r.tech_id} | label: {r.tech_label}\n"
                f"  phrases: {r.fragments}\n  sentences: {r.sentences}\n")
print(f"{len(tech)} technologies of {', '.join(ENGINES)} -> {OUT / 'technologies.txt'}")
