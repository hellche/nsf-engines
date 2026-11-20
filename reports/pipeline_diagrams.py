# The pipeline diagram in two parts (shown on reports/pipeline.Rmd):
#   nsf_engines_pipeline_kb.svg        1. knowledge base: sources -> registries -> classification -> outputs ->
#                                         filter -> knowledge base of each Engine
#   nsf_engines_pipeline_analysis.svg  2. analysis (in development): metrics and comparison groups, as lists;
#                                         on its own page, reports/analysis.Rmd, linked only from diagram 1
# Replaces nsf_engines_pipeline_v2.svg on the site (that file is kept as it was).
# Style: square corners, short cells, no file names, no middle dots; "(in progress)" marks what is not done yet.
# Run: python3 reports/pipeline_diagrams.py
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E = html.escape

STYLE = '''<defs>
<marker id="a" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#222"/></marker>
<marker id="A" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="16" markerHeight="16" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#111"/></marker>
<style>
text { font-family: Helvetica, Arial, "DejaVu Sans", sans-serif; }
.box { fill: #fff; stroke: #222; stroke-width: 1.5; }
.kb { fill: #fff; stroke: #111; stroke-width: 2.5; }
.frame { fill: none; stroke: #222; stroke-width: 1.5; }
.on { fill: #e3ecf9; stroke: #4a6fa5; stroke-width: 2.5; }
.off { fill: #f5f6f8; stroke: #c9d0da; stroke-width: 1.2; }
.t { font-size: 16px; font-weight: 700; fill: #111; text-anchor: middle; }
.ts { font-size: 13.5px; font-weight: 700; fill: #111; text-anchor: middle; }
.tf { font-size: 14.5px; font-weight: 700; fill: #111; text-anchor: middle; }
.s { font-size: 12px; fill: #555; text-anchor: middle; }
.n { font-size: 12px; fill: #111; text-anchor: middle; }
.wip { font-size: 11.5px; font-style: italic; fill: #b35900; text-anchor: middle; }
.cap { font-size: 12px; font-style: italic; fill: #555; text-anchor: middle; }
.offt { font-size: 13.5px; font-weight: 600; fill: #8a8f97; text-anchor: middle; }
.offs { font-size: 11.5px; fill: #a0a5ac; text-anchor: middle; }
.ons { font-size: 11.5px; fill: #2d3f5c; text-anchor: middle; }
.keybox { fill: #f8dfa6; stroke: #c27c00; stroke-width: 3.5; }
.keyt { font-size: 14.5px; font-weight: 700; fill: #6b4100; text-anchor: middle; text-decoration: underline; }
.keyl { font-size: 12px; font-weight: 700; fill: #6b4100; text-anchor: middle; }
a.key:hover .keybox { fill: #f3cd7e; }
.li { font-size: 13px; fill: #222; }
.lib { font-weight: 700; fill: #111; }
.ln { fill: none; stroke: #222; stroke-width: 1.5; }
.LN { fill: none; stroke: #111; stroke-width: 4; stroke-linejoin: round; }
.lg { font-size: 12px; fill: #444; }
</style></defs>'''


class Svg:
    def __init__(self):
        self.o = []

    def rect(self, cls, x, y, w, h):
        self.o.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>')

    def text(self, cls, x, y, t):
        self.o.append(f'<text class="{cls}" x="{x}" y="{y}">{E(t)}</text>')

    def path(self, cls, d, arrow=None):
        m = f' marker-end="url(#{arrow})"' if arrow else ""
        self.o.append(f'<path class="{cls}" d="{d}"{m}/>')

    def box(self, x, y, w, h, title, lines=(), cls="box", tcls="t", first=24, step=17):
        """A cell: title, then lines; a line is text, or ("wip", text) for 'in progress', or ("i", text) italic."""
        self.rect(cls, x, y, w, h)
        self.text(tcls, x + w / 2, y + first, title)
        for i, l in enumerate(lines):
            kind, t = (l if isinstance(l, tuple) else ("s", l))
            c = {"s": "s", "wip": "wip", "i": "s", "n": "n", "on": "ons", "off": "offs"}[kind]
            if kind == "i":
                self.o.append(f'<text class="s" x="{x + w / 2}" y="{y + first + 18 + i * step}" style="font-style:italic">{E(t)}</text>')
            else:
                self.text(c, x + w / 2, y + first + 18 + i * step, t)

    def cell(self, on, x, y, w, h, title, lines, extra=(), wip_title=None):
        self.rect("on" if on else "off", x, y, w, h)
        if wip_title:   # "(in progress)" right after the title, on the same line
            self.o.append(f'<text class="ts" x="{x + w / 2}" y="{y + 22}">{E(title)} '
                          f'<tspan style="font-size:11.5px;font-weight:400;font-style:italic;fill:#b35900">({E(wip_title)})</tspan></text>')
        else:
            self.text("ts" if on else "offt", x + w / 2, y + 22, title)
        for i, l in enumerate(lines):
            self.text("ons" if on else "offs", x + w / 2, y + 40 + i * 16, l)
        for i, l in enumerate(extra):
            self.text("wip", x + w / 2, y + 40 + (len(lines) + i) * 16, l)

    def listing(self, x, y, items, step=22):
        """A bullet list: (bold name, rest)."""
        for i, (b, rest) in enumerate(items):
            self.o.append(f'<text class="li" x="{x}" y="{y + i * step}">•  <tspan class="lib">{E(b)}</tspan>'
                          f'{E(": " + rest) if rest else ""}</text>')

    def listing_named(self, x, y, items, step=22):
        """A bullet list: what is measured, then the metric's name in brackets, in italics; nothing bold."""
        for i, (name, what) in enumerate(items):
            self.o.append(f'<text class="li" x="{x}" y="{y + i * step}">•  {E(what)} '
                          f'<tspan style="font-style:italic">({E(name)})</tspan></text>')

    def save(self, name, w, h, title):
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
               f'<title>{E(title)}</title>', STYLE, '<rect width="100%" height="100%" fill="#fff"/>'] + self.o + ['</svg>']
        (ROOT / name).write_text("\n".join(svg), encoding="utf-8")


# ---- 1. Knowledge base ----------------------------------------------------------------------------------------
# compact: a box with n text lines is hb(n) tall, rows are GAP apart
hb = lambda n: 36 + 16 * n
GAP = 32
s = Svg()
box = lambda x, y, w, title, lines, **k: s.box(x, y, w, hb(len(lines)), title, lines, first=22, step=16, **k)
T = 30
box(285, T, 300, "NSF website", ["PI, Co-PI, titles, abstracts"])
box(695, T, 300, "Engine websites", ["teams, partners"])
y1 = T + hb(1)
R = y1 + GAP
s.path("ln", f"M435,{y1} V{R - 2}", "a")
s.path("ln", f"M845,{y1} V{R - 2}", "a")
s.path("ln", f"M760,{y1} V{y1 + 16} H520 V{R - 2}", "a")
box(285, R, 300, "People registry", ["PI + people from the websites", ("n", "N = …")])
# ties between the people of the registry (NSF award + Engine websites): career sources still to collect
box(40, R, 175, "Ties between people", [("wip", "CV (in progress)"), ("wip", "LinkedIn (in progress)"),
    ("wip", "Revelio (in progress)"), ("i", "careers, shared employers")], tcls="ts")
s.path("ln", f"M215,{R + hb(2) / 2} H283", "a")
box(695, R, 300, "Partner registry", ["all organisations mentioned", ("n", "N = …")])
C = R + hb(2) + GAP                                     # classification frames
s.path("ln", f"M435,{R + hb(2)} V{C - 2}", "a")
s.path("ln", f"M845,{R + hb(2)} V{C - 2}", "a")
CH, R1, R2 = 64, C + 36, C + 36 + 64 + 8                 # cell height, rows
FH = R2 + CH + 10 - C
for x0, title, cells in ((250, "LLM: people, 4 roles",
                          [(False, "Corporate R&D", ["CTO, company patents", "→ via the partner"]),
                           (False, "Organiser", ["chambers, foundations", "economic development"]),
                           (True, "Researcher", ["works in OpenAlex", "h-index, patents"]),
                           (True, "Research administrator", ["VP for Research, provost", "institute director"])]),
                         (660, "LLM: partners, 4 types",
                          [(False, "Users", ["plants, operators", "few works and patents"]),
                           (False, "Intermediaries", ["incubators, venture", "clusters"]),
                           (True, "Knowledge producers", ["universities, national labs", "ERC, corporate R&D"]),
                           (False, "Workforce, community", ["colleges, workforce", "training programmes"])])):
    s.rect("frame", x0, C, 370, FH)
    s.text("tf", x0 + 185, C + 24, title)
    for i, (on, t, l) in enumerate(cells):
        s.cell(on, x0 + 12 + (i % 2) * 178, R1 if i < 2 else R2, 168, CH, t, l)
# matching: extra checks of who is who
MY = C + 40
box(40, MY, 175, "People matching", ["OpenAlex author ID", ("wip", "ORCID (in progress)"),
    "PatentsView inventor", ("i", "name + current org.")], tcls="ts")
s.path("ln", f"M215,{MY + hb(4) / 2} H248", "a")
box(1065, MY, 185, "Organisation matching", [("wip", "ROR (in progress)"), "OpenAlex institutions",
    "PatentsView assignee", ("i", "name + US location")], tcls="ts")
s.path("ln", f"M1065,{MY + hb(4) / 2} H1032", "a")
B = R2 + CH                                             # bottom of the "on" cells
W = C + FH + GAP + 6                                    # works and patents
s.path("LN", f"M346,{B} V{B + 20} H524 V{B}")
s.path("LN", f"M435,{B + 20} V{W - 2}", "A")
s.path("LN", f"M756,{B} V{B + 20} H845 V{W - 2}", "A")
WH = hb(3)
box(285, W, 300, "People's works and patents", ["by author and inventor ID", ("n", "N OpenAlex ID = …"),
    ("n", "N patent ID = …")])
s.box(695, W, 300, WH, "Organisations' works and patents", [("n", "N OpenAlex org ID = …"), ("n", "N patent assignee = …")],
      first=22, step=16)
# researchers at the partners (step 6e): authors of the partners' works, added to the people's works
s.path("ln", f"M695,{W + WH / 2} H587", "a")
s.text("cap", 640, W + WH / 2 - 6, "authors")
F = W + WH + GAP + 6                                    # output filter
s.path("LN", f"M435,{W + WH} V{F - 2}", "A")
s.path("LN", f"M845,{W + WH} V{F - 2}", "A")
FC = 64
s.rect("frame", 330, F, 620, 50 + FC + 10)
s.text("tf", 640, F + 22, "Output filter")
s.text("s", 640, F + 40, "each condition applied or flagged")
s.cell(True, 545, F + 50, 190, FC, "Time", ["from (award − 5 years)", "onwards"])
s.cell(True, 745, F + 50, 190, FC, "Geography", ["Engine's states", "affiliation, inventor address"], wip_title="in progress")
s.cell(True, 345, F + 50, 190, FC, "Technology", ["OpenAlex topics", "+ CPC classes"])
FB = F + 50 + FC + 10                                   # bottom of the filter frame
# the key cell, in the v1 orange: a link to the Technology profile page (methodology.html), clickable as a whole
PRO_Y = F + 50 + FC / 2
s.o.append('<a href="methodology.html" class="key">')
s.rect("keybox", 40, PRO_Y - 38, 175, 76)
s.text("keyt", 127.5, PRO_Y - 13, "Technology profile")
s.text("s", 127.5, PRO_Y + 6, "methodology")
s.text("keyl", 127.5, PRO_Y + 25, "open the page →")
s.o.append('</a>')
# the grant texts also feed the technology profile: a line down the left edge, into the top of the cell
s.path("ln", f"M285,{T + hb(1) / 2} H22 V{PRO_Y - 54} H127.5 V{PRO_Y - 40}", "a")
s.text("cap", 153, T + hb(1) / 2 - 8, "award titles and abstracts")
s.path("ln", f"M215,{PRO_Y} H328", "a")
K = FB + GAP + 6                                        # knowledge base
s.path("LN", f"M640,{FB} V{K - 2}", "A")
box(490, K, 300, "Engine knowledge base", [("n", "1) people + organisations"),
    "12 Engines, N works, N patents", ("wip", "2) top works by others (in progress)")], cls="kb")
box(40, K - 8, 175, "Top past grants", ["and publications", "same 5 years, same topic",
    "search all vs by authors", ("wip", "(in progress)")], tcls="ts")
s.path("ln", f"M215,{K + hb(3) / 2} H488", "a")
E2 = K + hb(3)
s.path("LN", f"M640,{E2} V{E2 + 34}", "A")
s.o.append('<a href="analysis.html" class="next">')          # the only link to the Analysis page
s.text("cap", 640, E2 + 50, "next: metrics and comparison groups")
s.o.append('</a>')
s.save("nsf_engines_pipeline_kb.svg", 1290, E2 + 64, "NSF Engines: knowledge base")

# ---- 2. Analysis (in development) -------------------------------------------------------------------------------
a = Svg()
a.o.append('<a href="pipeline.html">')                       # back to the pipeline
a.box(490, 20, 300, 56, "Engine knowledge base", ["from the pipeline"], cls="kb")
a.o.append('</a>')
a.path("LN", "M640,76 V108", "A")
M = 110
metrics = [("Volume and LQ", "the region's share of the technology relative to the US"),
           ("Collaboration", "share of joint works within the region"),
           ("Local patents", "share of assignees from the region"),
           ("Partner network before the award", "joint works and patents, partner × partner"),
           ("Knowledge sources", "whom the base cites: region, US, world"),
           ("Reliance on science", "patent → paper citations from the region's patents")]
MH = 62 + 22 * len(metrics)
a.rect("frame", 250, M, 780, MH)
a.text("tf", 640, M + 26, "Metrics")
a.text("s", 640, M + 44, "for each Engine")
a.listing_named(285, M + 72, metrics)
a.box(1065, M + MH / 2 - 34, 205, 68, "Patent → paper links", [("wip", "check SciSciNet?")], tcls="ts",
      first=22, step=16)
a.path("ln", f"M1065,{M + MH / 2} H1032", "a")
G = M + MH + 40
a.path("LN", f"M640,{M + MH} V{G - 2}", "A")
groups = [("Finalists that lost", "3 finalists + 14 semi-finalists: what sets the winner apart?"),
          ("Georgia", "12 profiles × the state of GA: where do we stand?"),
          ("Technology leaders", "all states: why here?"),
          ("Same region", "other technologies")]
GH = 44 + 22 * len(groups)
a.rect("frame", 250, G, 780, GH)
a.text("tf", 640, G + 26, "Comparison groups")
a.listing(285, G + 54, groups)
a.box(1065, G + GH / 2 - 42, 205, 84, "Competition funnel", [("wip", "available?"), "applications → finals"], tcls="ts")
a.path("ln", f"M1065,{G + GH / 2} H1032", "a")
a.save("nsf_engines_pipeline_analysis.svg", 1290, G + GH + 30, "NSF Engines: metrics and comparison groups (in development)")
print("written: nsf_engines_pipeline_kb.svg, nsf_engines_pipeline_analysis.svg")
