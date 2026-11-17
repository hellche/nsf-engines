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
def rect(cls, x, y, w, h, rx=3): o.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>')
def text(cls, x, y, t): o.append(f'<text class="{cls}" x="{x}" y="{y}">{E(t)}</text>')
def down(x, y1, y2, cls="ln", m="a"): o.append(f'<path class="{cls}" d="M{x},{y1} V{y2-3}" marker-end="url(#{m})"/>')
def elbow(x1, y1, x2, y2, cls="ln"): o.append(f'<path class="{cls}" d="M{x1},{y1} V{(y1+y2)/2} H{x2} V{y2-3}" marker-end="url(#a)"/>')
def box(cls, x, y, w, h, title, lines=()):
    rect(cls, x, y, w, h)
    text("t", x + w/2, y + (24 if lines else h/2 + 5), title)
    for i, l in enumerate(lines):
        text("s", x + w/2, y + 44 + i*17, l)
def badge(x, y):
    rect("km", x, y, 104, 20, 10); text("kmt", x + 52, y + 14, "знания модели")

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
H3 = 320
rect("common", CX, Y3, CWD, H3, 8)
text("bt", CX + 18, Y3 + 28, "Технологии гранта · общий шаг для v1 и v3.1")
text("bs", CX + 18, Y3 + 48, "каждый промпт: 3 независимых прогона; модель выписывает фразы")
text("bs", CX + 18, Y3 + 65, "гранта дословно и группирует их в технологии")
PY, PH, PW = Y3 + 92, 76, 236
px = [CX + 22 + i*((CWD - 44 - PW)/2) for i in range(3)]
for x, (t, sub, cls) in zip(px, [("Простой", "только идея задачи", "pr"), ("Простой +", "идея + крупность технологий", "chosen"), ("Длинный", "правила и примеры", "pr")]):
    box(cls, x, PY, PW, PH, t, [sub])
text("tag", px[1] + PW - 8, PY - 8, "выбран")
TY, TW = PY + PH + 60, 600
MID = CX + CWD/2
TX = MID - TW/2
o.append(f'<path class="LN" d="M{px[1]+PW/2},{PY+PH} V{TY-4}" marker-end="url(#A)"/>')
for x in (px[0], px[2]):
    o.append(f'<path class="dl" d="M{x+PW/2},{PY+PH} V{PY+PH+22}"/>')
    text("note", x + PW/2, PY + PH + 38, "сравнили, не взяли")
rect("tech", TX, TY, TW, 64, 6)
text("t", MID, TY + 26, "Технологии гранта: 43 технологии, 2–5 на Engine")
text("s", MID, TY + 46, "77 фраз, найденных ≥ 2 прогонами из 3 · разбиение самого согласованного прогона")
# v1 lane below
LY = Y3 + H3 + 50
elbow(MID - TW/4, TY + 64, cx[0], LY)
elbow(MID + TW/4, TY + 64, cx[1], LY + 10)
box("box", cols[0], LY, CW, 96, "Модель выбирает по уровням",
    ["CPC: подкласс (из 652) → группы внутри", "OpenAlex: подобласть (из 250) → темы внутри", "промпт v1_select_by_levels.md"])
badge(cols[0] + CW - 112, LY - 10)
down(cx[0], LY + 96, LY + 126)
box("box", cols[0], LY + 126, CW, 80, "3 независимых прогона",
    ["в итог: пункты, выбранные ≥ 2 прогонами", "совпадение с другим прогоном: группы CPC 91% · темы 86%"])
down(cx[0], LY + 206, LY + 236)
box("out1", cols[0], LY + 236, CW, 84, "Профиль v1",
    ["162 пункта: 84 группы CPC + 78 тем OpenAlex", "до 2 тем и 2 групп CPC; у всех 43 технологий есть оба"])
text("note", cx[1], LY + 34, "v3.1: пересчитать на новых технологиях")
# legend
L = LY + 366
items = [("chosen", "выбранный промпт"), ("pr", "сравнили, не взяли"), ("km", "знания модели о предметной области")]
x = FULL_X
for c, t in items:
    rect(c, x, L - 13, 30, 18, 3); text("lg", x + 38, L + 1, t); x += 38 + 8*len(t) + 40
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
