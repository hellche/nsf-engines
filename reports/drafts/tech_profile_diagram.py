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
for x, h, k in zip(cols, ["v1 · LLM brute force", "v3.1 · embeddings, more nuance", "v2 · embeddings"], ["h1", "h3", "h2"]):
    rect(f"head {k}", x, 20, CW, 46); text("th", x + CW/2, 49, h)
# 2. grants
Y2 = 100
box("box", FULL_X, Y2, FULL_W, 60, "12 грантов NSF", ["название + аннотация · 203 предложения · NSF Award API"])
# common step for v1 and v3.1
Y3 = Y2 + 120
CX, CWD = cols[0], cols[1] + CW - cols[0]          # the common block spans the v1 and v3.1 columns
for i in (0, 1):
    down(cx[i], Y2 + 60, Y3)
H3 = 86 + 60 + 48 + 60 + 18                         # header, prompts, gap, technologies block, padding
rect("common", CX, Y3, CWD, H3)                      # background first, the content is drawn on top
text("bt", CX + 18, Y3 + 28, "Технологии гранта · общий шаг для v1 и v3.1")
text("bs", CX + 18, Y3 + 48, "каждый промпт: 3 независимых прогона; модель выписывает фразы")
text("bs", CX + 18, Y3 + 65, "гранта дословно и группирует их в технологии")
PY, PH, PW = Y3 + 86, 60, 236
px = [CX + 22 + i*((CWD - 44 - PW)/2) for i in range(3)]
for x, (t, sub, cls) in zip(px, [("Простой", "только идея задачи", "pr"), ("Простой +", "идея + крупность технологий", "chosen"), ("Длинный", "правила и примеры", "pr")]):
    box(cls, x, PY, PW, PH, t, [sub])
text("tag", px[1] + PW - 8, PY - 8, "выбран")
TY, TW, TH = PY + PH + 48, 600, 60
MID = CX + CWD/2
TX = MID - TW/2
o.append(f'<path class="LN" d="M{px[1]+PW/2},{PY+PH} V{TY-4}" marker-end="url(#A)"/>')
for x in (px[0], px[2]):
    o.append(f'<path class="dl" d="M{x+PW/2},{PY+PH} V{PY+PH+16}"/>')
    text("note", x + PW/2, PY + PH + 31, "сравнили, не взяли")
rect("tech", TX, TY, TW, TH)
text("t", MID, TY + 26, "Технологии гранта: 43 технологии, 2–5 на Engine")
text("s", MID, TY + 46, "77 фраз, найденных ≥ 2 прогонами из 3 · разбиение самого согласованного прогона")
# codes: our lists, common to v1 and v3.1; narrow, so the technology arrows pass straight down beside it
CY, CH, CBW = Y3 + H3 + 36, 150, 500
CBX = MID - CBW/2
rect("common", CBX, CY, CBW, CH)
text("bt", CBX + 16, CY + 26, "Коды OpenAlex и CPC")
text("bs", CBX + 16, CY + 44, "наши списки, общие для v1 и v3.1")
SW = 220
sx = [CBX + 20, CBX + CBW - 20 - SW]
box("box", sx[0], CY + 58, SW, 76, "Крупные категории", ["652 подкласса CPC", "250 подобластей OpenAlex"])
box("box", sx[1], CY + 58, SW, 76, "Полные списки", ["7 646 групп CPC", "4 516 тем OpenAlex"])
PRY = CY + CH + 44
tx = [TX + 15, TX + TW - 15]                         # technologies: straight down, outside the codes block
kx = [sx[0] + SW/2, sx[1] + SW/2]                    # codes: straight down from each list
for i in (0, 1):
    down(tx[i], TY + TH, PRY)
    down(kx[i], CY + 134, PRY)
    text("note", kx[i] + (22 if i == 0 else -22), PRY - 12, "коды")
text("note", (tx[0] + kx[0])/2, PRY - 12, "технологии")
text("note", (tx[1] + kx[1])/2, PRY - 12, "технологии")
# v1: the model matches each technology to our codes, three times
LH = 92
rect("llm", cols[0], PRY, CW, LH)
text("t", cx[0], PRY + 24, "Выбор LLM: соотнести технологии с кодами")
# the two levels as a picture: a coarse category first, then a code inside it
QW, QH, QG = 130, 34, 46
q0 = cx[0] - QW - QG/2
for k, label in enumerate(["Крупная категория", "Код внутри неё"]):
    rect("q", q0 + k*(QW + QG), PRY + 40, QW, QH)
    text("qs", q0 + k*(QW + QG) + QW/2, PRY + 62, label)
o.append(f'<path class="ln" d="M{q0+QW},{PRY+57} H{q0+QW+QG-3}" marker-end="url(#a)"/>')
text("tag", cols[0] + CW - 12, PRY + 62, "× 3")
RY = PRY + LH + 30
down(cx[0], PRY + LH, RY)
box("out1", cols[0], RY, CW, 74, "Профиль v1",
    ["≥ 2 прогонов из 3 · совпадение: группы CPC 91%, темы 86%", "162 пункта: 84 группы CPC + 78 тем OpenAlex"])
# v3.1, steps 1-2 only (step 3 is still being discussed)
def mini_flow(y, labels, out):
    """small cells side by side, arrows from each into one result cell below"""
    n, w, g = len(labels), 96, 14
    x0 = cx[1] - (n*w + (n-1)*g)/2
    for k, lab in enumerate(labels):
        rect("q", x0 + k*(w + g), y, w, 30)
        text("qs", x0 + k*(w + g) + w/2, y + 20, lab)
        o.append(f'<path class="ln" d="M{x0+k*(w+g)+w/2},{y+30} V{y+44}"/>')
    o.append(f'<path class="ln" d="M{x0+w/2},{y+44} H{x0+(n-1)*(w+g)+w/2}"/>')
    o.append(f'<path class="ln" d="M{cx[1]},{y+44} V{y+55}" marker-end="url(#a)"/>')
    rect("q", cx[1] - 120, y + 58, 240, 28)
    text("qs", cx[1], y + 77, out)
S1H = 136
rect("emb", cols[1], PRY, CW, S1H)
text("t", cx[1], PRY + 24, "1 · Эмбеддинги в двух моделях")
mini_flow(PRY + 38, ["77 фраз", "темы / CPC"], "Близость: косинус")
S2Y = PRY + S1H + 30
down(cx[1], PRY + S1H, S2Y)
rect("emb", cols[1], S2Y, CW, S1H)
text("t", cx[1], S2Y + 24, "2 · От фраз к технологии")
mini_flow(S2Y + 38, ["max", "centroid", "mix"], "Один рейтинг · топ-20")
RY3 = S2Y + S1H - 74
# legend
L = max(RY, RY3) + 74 + 46
items = [("chosen", "выбранный промпт"), ("pr", "сравнили, не взяли / ещё не сделано"),
         ("llm", "выбор LLM по нашим спискам"), ("emb", "эмбеддинги (v3.1)")]
x = FULL_X
for c, t in items:
    rect(c, x, L - 13, 30, 18); text("lg", x + 38, L + 1, t); x += 38 + 8*len(t) + 40
H = L + 30
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
 '<title>Профиль технологии: версии v1, v2, v3.1 (в работе)</title>',
 '''<defs>
<marker id="a" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#222"/></marker>
<marker id="A" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="14" markerHeight="14" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#111"/></marker>
<style>
text { font-family: Helvetica, Arial, "DejaVu Sans", sans-serif; }
.box { fill: #fff; stroke: #222; stroke-width: 1.5; }
.v2 { fill: #e3ecf9; stroke: #4a6fa5; stroke-width: 1.5; }
.head { fill: #fff; stroke: #222; stroke-width: 1.5; }
.h2 { stroke: #4a6fa5; } .h3 { stroke: #4f8a62; }
.common { fill: #fafafa; stroke: #444; stroke-width: 1.5; }
.pr { fill: #fff; stroke: #999; stroke-width: 1.5; stroke-dasharray: 6 4; }
.chosen { fill: #fff; stroke: #111; stroke-width: 3; }
.tech { fill: #fff6e5; stroke: #b07a1a; stroke-width: 2.5; }
.out1 { fill: #f0f0f0; stroke: #222; stroke-width: 2.5; }
.q { fill: #fff; stroke: #222; stroke-width: 1.2; }
.qs { font-size: 12.5px; fill: #222; text-anchor: middle; }
.qss { font-size: 11.5px; fill: #555; text-anchor: middle; }
.emb { fill: #e6f2ea; stroke: #4f8a62; stroke-width: 2; }
.llm { fill: #fbe9dc; stroke: #c0632b; stroke-width: 2; }
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
