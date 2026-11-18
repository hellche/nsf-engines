# Draft diagram of the technology profile versions (in progress, not on the site).
# Run: python3 reports/drafts/tech_profile_diagram.py reports/drafts/tech_profile_diagram.svg
import html, sys
E = html.escape
X0, CW, GAP = 40, 380, 30
cols = [X0 + i*(CW+GAP) for i in range(3)]
cx = [x + CW/2 for x in cols]
W = cols[2] + CW + X0
FULL_X, FULL_W = cols[0], cols[2] + CW - cols[0]
o = []
def rect(cls, x, y, w, h): o.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>')   # square corners, as the pipeline diagram
def text(cls, x, y, t): o.append(f'<text class="{cls}" x="{x}" y="{y}">{E(t)}</text>')
def down(x, y1, y2, cls="ln", m="a"): o.append(f'<path class="{cls}" d="M{x},{y1} V{y2-3}" marker-end="url(#{m})"/>')
def elbow(x1, y1, x2, y2, cls="ln"): o.append(f'<path class="{cls}" d="M{x1},{y1} V{(y1+y2)/2} H{x2} V{y2-3}" marker-end="url(#a)"/>')
def box(cls, x, y, w, h, title, lines=()):
    rect(cls, x, y, w, h)
    text("t", x + w/2, y + (24 if lines else h/2 + 5), title)
    for i, l in enumerate(lines):
        text("s", x + w/2, y + 44 + i*17, l)

# 1. versions
for x, h, k in zip(cols, ["v1: LLM brute force", "v3.1: embeddings, more nuance", "v2: embeddings"], ["h1", "h3", "h2"]):
    rect(f"head {k}", x, 20, CW, 46); text("th", x + CW/2, 49, h)
# 2. grants
Y2 = 100
box("box", FULL_X, Y2, FULL_W, 60, "12 NSF awards", ["title + abstract (NSF website)"])
# common step for v1 and v3.1
Y3 = Y2 + 120
CX, CWD = cols[0], cols[1] + CW - cols[0]          # the common block spans the v1 and v3.1 columns
H3 = 66 + 60 + 48 + 60 + 22                         # header, prompts, gap, technologies block, padding
rect("prompts", CX, Y3, CWD, H3)                     # background first, the content is drawn on top
text("bt", CX + 18, Y3 + 30, "LLM prompts to find the grant's technologies")
PY, PH, PW = Y3 + 66, 60, 236
px = [CX + 22 + i*((CWD - 44 - PW)/2) for i in range(3)]
for x, (t, sub, cls) in zip(px, [("Simple", "the task only", "pr"), ("Simple +", "task + size of a technology", "chosen"), ("Long", "rules and examples", "pr")]):
    box(cls, x, PY, PW, PH, t, [sub])
TY, TW, TH = PY + PH + 48, 600, 60
MID = CX + CWD/2
TX = MID - TW/2
# vertical axes of v1 and v3.1 = the two lines that leave the technologies block (the reference)
AX = [TX + 15, TX + TW - 15]
for i in (0, 1):
    o.append(f'<path class="ln" d="M{AX[i]},66 V{Y2}"/>')       # header -> grants
    down(AX[i], Y2 + 60, Y3)                                    # grants -> prompts
o.append(f'<path class="ln" d="M{cx[2]},66 V{Y2}"/>')           # v2: header -> grants
o.append(f'<path class="LN" d="M{px[1]+PW/2},{PY+PH} V{TY-4}" marker-end="url(#A)"/>')
o.append(f'<text class="x3" x="{px[1]+PW/2+12}" y="{(PY+PH+TY)/2+6}">× 3</text>')
rect("tech", TX, TY, TW, TH)
text("t", MID, TY + 26, "43 technologies, 2–5 per Engine")
text("s", MID, TY + 46, "77 phrases found by ≥ 2 of 3 runs")
# codes: our lists, common to v1 and v3.1; narrow, so the technology arrows pass straight down beside it
CY, CH = Y3 + H3 + 36, 150
SW = 220
tx = AX[:]                         # technologies: straight down, outside the codes block
kx = [2*cx[i] - tx[i] for i in (0, 1)]               # list centre mirrors the technology line about the column axis
sx = [k - SW/2 for k in kx]
CBX, CBW = sx[0] - 20, sx[1] + SW + 20 - (sx[0] - 20)
rect("common", CBX, CY, CBW, CH)
text("bt", CBX + 16, CY + 26, "OpenAlex and CPC codes")
box("box", sx[0], CY + 58, SW, 76, "Coarse categories", ["652 CPC subclasses", "250 OpenAlex subfields"])
box("box", sx[1], CY + 58, SW, 76, "Full lists", ["7,646 CPC groups", "4,516 OpenAlex topics"])
PRY = CY + CH + 44
BY = PRY - 18                                        # brackets: technologies + list -> one arrow on the column axis
for i in (0, 1):
    for x0, y0 in ((tx[i], TY + TH), (kx[i], CY + 134)):
        o.append(f'<path class="LN2" d="M{x0},{y0} V{BY}"/>')
    o.append(f'<path class="LN2" d="M{min(tx[i], kx[i])},{BY} H{max(tx[i], kx[i])}"/>')
    down(cx[i], BY, PRY)
# v1: the model matches each technology to our codes, three times
LH = 92
rect("llm", cols[0], PRY, CW, LH)
text("t", cx[0], PRY + 24, "LLM prompt: match technologies to codes")
# the two levels as a picture: a coarse category first, then a code inside it
QW, QH, QG = 130, 34, 46
q0 = cx[0] - QW - QG/2
for k, label in enumerate(["Coarse category", "Code inside it"]):
    rect("q", q0 + k*(QW + QG), PRY + 40, QW, QH)
    text("qs", q0 + k*(QW + QG) + QW/2, PRY + 62, label)
o.append(f'<path class="ln" d="M{q0+QW},{PRY+57} H{q0+QW+QG-3}" marker-end="url(#a)"/>')
text("tag", cols[0] + CW - 12, PRY + 62, "× 3")
RY = PRY + LH + 30
down(cx[0], PRY + LH, RY)
box("out1", cols[0], RY, CW, 74, "Profile v1",
    ["≥ 2 of 3 runs; agreement: CPC groups 91%, topics 86%", "162 items: 84 CPC groups + 78 OpenAlex topics"])
# v3.1 (simple), step 1: embeddings. Two columns: topics (SPECTER2) and CPC groups (PatentSBERTa); each
# compares the 43 technologies with the full list by geometric closeness; picture: a technology and its nearest items
EH = 480
rect("emb", cols[1], PRY, CW, EH)
text("t", cx[1], PRY + 26, "Embeddings")
w, g = 164, 22
ex = [cx[1] - w - g/2, cx[1] + g/2]
for k, (lst, lsub, model, near) in enumerate([("4,516 OpenAlex topics", "name, description, keywords", "SPECTER2", "OpenAlex"),
                                              ("7,646 CPC groups", "subclass, group, subgroups", "PatentSBERTa", "CPC")]):
    xm = ex[k] + w/2
    rect("frame", ex[k] - 5, PRY + 39, w + 10, 120)         # the pair that the model compares
    rect("q", ex[k], PRY + 44, w, 42); text("qs", xm, PRY + 62, "43 technologies"); text("qss", xm, PRY + 78, "label + phrases")
    text("plus", xm, PRY + 104, "+")
    rect("q", ex[k], PRY + 112, w, 42); text("qs", xm, PRY + 130, lst); text("qss", xm, PRY + 146, lsub)
    down(xm, PRY + 159, PRY + 172)
    rect("model", ex[k], PRY + 172, w, 30); text("qs", xm, PRY + 192, model)
    down(xm, PRY + 202, PRY + 218)
    if k == 0: rect("q", xm - 50, PRY + 218, 100, 100)          # topics: square, as in the picture below
    else: o.append(f'<circle class="q" cx="{xm}" cy="{PRY+268}" r="50"/>')   # CPC: circle
    text("qs", xm, PRY + 258, "geometric"); text("qs", xm, PRY + 274, "closeness"); text("qss", xm, PRY + 292, near)
# picture: one technology in the middle, its nearest topics (squares) and CPC groups (circles)
SC = (cx[1], PRY + 392)
for xm in (ex[0] + w/2, ex[1] + w/2):
    o.append(f'<path class="ln" d="M{xm},{PRY+318} L{SC[0] + (xm - SC[0])*0.25},{SC[1]-24}" marker-end="url(#a)"/>')
# ray length = distance; inside the dashed boundary: the 50 nearest (go to the judge), outside: faded
import math
RX, RY = 128, 54
o.append(f'<ellipse class="bound" cx="{SC[0]}" cy="{SC[1]}" rx="{RX}" ry="{RY}"/>')
pts = [(142, .78), (168, .62), (193, .74), (218, .86), (160, 1.25), (182, 1.27), (203, 1.32)]
for side in (-1, 1):                      # left: topics (squares), right: CPC groups (circles)
    for ang, t in pts:
        a_ = math.radians(ang if side < 0 else 180 - ang)
        x, y = SC[0] + t*RX*math.cos(a_), SC[1] + t*RY*math.sin(a_)
        far = ' style="opacity:.3"' if t > 1 else ''
        o.append(f'<g{far}><path class="ln" d="M{SC[0]},{SC[1]} L{x:.1f},{y:.1f}"/>')
        o.append(f'<rect class="q" x="{x-8:.1f}" y="{y-8:.1f}" width="16" height="16"/></g>' if side < 0 else
                 f'<circle class="q" cx="{x:.1f}" cy="{y:.1f}" r="8"/></g>')
o.append(f'<ellipse class="tc" cx="{SC[0]}" cy="{SC[1]}" rx="40" ry="18"/>')
text("qss", SC[0], SC[1] + 4, "technology")
text("qss", SC[0] - 110, SC[1] + RY + 18, "50 nearest topics")
text("qss", SC[0] + 110, SC[1] + RY + 18, "50 nearest CPC groups")
# step 3: an LLM judge scores the 50 candidates of each list, three runs
# v2: the grant text as it is (title + each abstract sentence), then the same embeddings as v3.1;
# without the technologies step the rankings are noisy (region, workforce), so v2 stops here
down(cx[2], Y2 + 60, PRY)
box("v2c", cols[2], PRY, CW, 96, "Embeddings on the full texts", ["no LLM step to clean the abstracts",
    "title + full abstract (sentence by sentence)", "embeddings as in v3.1 give noise (region, workforce)"])
JY = PRY + EH + 30
down(cx[1], PRY + EH, JY)
rect("judge", cols[1], JY, CW, LH)
text("t", cx[1], JY + 24, "LLM judge: score the candidates")
q1 = cx[1] - QW - QG/2
for k, label in enumerate(["50 nearest", "Score 0–3"]):
    rect("q", q1 + k*(QW + QG), JY + 40, QW, QH)
    text("qs", q1 + k*(QW + QG) + QW/2, JY + 62, label)
o.append(f'<path class="ln" d="M{q1+QW},{JY+57} H{q1+QW+QG-3}" marker-end="url(#a)"/>')
text("tag", cols[1] + CW - 12, JY + 62, "× 3")
RY3 = JY + LH + 30
down(cx[1], JY + LH, RY3)
box("pr", cols[1], RY3, CW, 74, "Profile v3.1",
    ["up to 2 topics and 2 CPC groups per technology", "high score in ≥ 2 of 3 runs"])
L = max(RY, RY3) + 74
H = L + 20
# Palette: Okabe-Ito orange #E69F00 (v1), sky blue #56B4E9 / blue #0072B2 (v3.1), reddish purple #CC79A7 (v2);
# tints for fills, darker shades for borders; checked for protan-, deutan- and tritanopia (Machado 2009): the v1
# and v3.1 fills differ by dE >= 33 in all three. The v2 cell border is as thin as the v2 header.
# No CSS comments in the style: the SVG is inlined into an R Markdown page, and pandoc reads "/* ... */" as
# Markdown emphasis, which breaks the SVG.
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
 '<title>Technology profile: versions v1, v2, v3.1 (in progress)</title>',
 '''<defs>
<marker id="a" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#222"/></marker>
<marker id="A" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#111"/></marker>
<style>
text { font-family: Helvetica, Arial, "DejaVu Sans", sans-serif; }
.box { fill: #fff; stroke: #222; stroke-width: 1.5; }
.v2 { fill: #e3ecf9; stroke: #4a6fa5; stroke-width: 1.5; }
.head { fill: #fff; stroke: #222; stroke-width: 1.5; }
.h2 { stroke: #cc79a7; } .h3 { fill: #c2e4f7; stroke: #0072b2; } .h1 { fill: #f8dfa6; stroke: #c27c00; }
.common { fill: #fff; stroke: #444; stroke-width: 1.5; }
.prompts { fill: #fff; stroke: #444; stroke-width: 1.5; }
.model { fill: #fff; stroke: #222; stroke-width: 2; }
.frame { fill: #fff; stroke: #111; stroke-width: 2; }
.judge { fill: #c2e4f7; stroke: #0072b2; stroke-width: 2; }
.v2c { fill: #fff; stroke: #cc79a7; stroke-width: 1.5; }
.bound { fill: none; stroke: #0072b2; stroke-width: 1.5; stroke-dasharray: 5 4; }
.tc { fill: #fff; stroke: #111; stroke-width: 2; }
.plus { font-size: 18px; font-weight: 700; fill: #222; text-anchor: middle; }
.x3 { font-size: 14px; font-weight: 700; fill: #111; }
.LN2 { fill: none; stroke: #222; stroke-width: 1.5; }
.pr { fill: #fff; stroke: #999; stroke-width: 1.5; stroke-dasharray: 6 4; }
.chosen { fill: #fff; stroke: #111; stroke-width: 3; }
.tech { fill: #fff; stroke: #111; stroke-width: 3; }
.out1 { fill: #fff; stroke: #222; stroke-width: 2.5; }
.q { fill: #fff; stroke: #222; stroke-width: 1.2; }
.qs { font-size: 12.5px; fill: #222; text-anchor: middle; }
.qss { font-size: 11.5px; fill: #555; text-anchor: middle; }
.emb { fill: #c2e4f7; stroke: #0072b2; stroke-width: 2; }
.llm { fill: #f8dfa6; stroke: #c27c00; stroke-width: 2; }
.stop { fill: #fdecea; stroke: #b3261e; stroke-width: 2; }
.km { fill: #fbe9dc; stroke: #c0632b; stroke-width: 1.2; }
.kmt { font-size: 11px; font-weight: 700; fill: #9a4a1c; text-anchor: middle; }
.th { font-size: 16px; font-weight: 700; fill: #111; text-anchor: middle; }
.t { font-size: 15px; font-weight: 700; fill: #111; text-anchor: middle; }
.stopt { font-size: 15px; font-weight: 700; fill: #b3261e; text-anchor: middle; }
.s { font-size: 12.5px; fill: #555; text-anchor: middle; }
.bt { font-size: 15px; font-weight: 700; fill: #222; }
.bs { font-size: 12.5px; fill: #555; }
.note { font-size: 12px; font-style: italic; fill: #888; text-anchor: middle; }
.tag { font-size: 11.5px; font-weight: 700; fill: #111; text-anchor: end; }
.lg { font-size: 12px; fill: #444; }
.ln { fill: none; stroke: #222; stroke-width: 1.5; }
.LN { fill: none; stroke: #111; stroke-width: 3; }
.dl { fill: none; stroke: #999; stroke-width: 1.5; stroke-dasharray: 5 4; }
</style></defs>''', '<rect width="100%" height="100%" fill="#fff"/>'] + o + ['</svg>']
open(sys.argv[1], 'w').write("\n".join(svg))
