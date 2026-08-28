#!/usr/bin/env python3
"""WTS-100 batch sequence state diagram."""
import pathlib, subprocess
W, H = 1500, 940
P=[]
def add(s): P.append(s)

def box(x,y,w,h,tag,lines,fill="#fff"):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="#000" stroke-width="1.8"/>')
    add(f'<text x="{x+w/2}" y="{y+25}" class="st">{tag}</text>')
    for i,l in enumerate(lines):
        add(f'<text x="{x+w/2}" y="{y+45+i*15}" class="ac">{l}</text>')

def arr(x1,y1,x2,y2,label="",lx=None,ly=None,dash=False):
    d = ' stroke-dasharray="6,4"' if dash else ''
    add(f'<path d="M {x1} {y1} L {x2} {y2}" stroke="#000" stroke-width="1.8" fill="none"{d} marker-end="url(#a)"/>')
    if label: add(f'<text x="{lx}" y="{ly}" class="cd">{label}</text>')

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add('''<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M 0 0 L 10 5 L 0 10 z" fill="#000"/></marker><style>
 text{font-family:Helvetica,Arial,sans-serif;text-anchor:middle;fill:#000}
 .st{font-size:16px;font-weight:700}
 .ac{font-size:10.5px}
 .cd{font-size:11px;font-weight:700;fill:#8a6d00}
 .h1{font-size:17px;font-weight:700;text-anchor:start}
 .h2{font-size:10px;text-anchor:start}
 .nt{font-size:10.5px;text-anchor:start}
 .ntb{font-size:11px;text-anchor:start;font-weight:700}
</style></defs>''')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
add(f'<rect x="12" y="12" width="{W-24}" height="{H-24}" fill="none" stroke="#000" stroke-width="1"/>')
add('<text x="34" y="44" class="h1">POU_SEQUENCE   batch state machine</text>')
add('<text x="34" y="61" class="h2">WTS-100 Water Treatment and Transfer Skid   |   one state active at a time   |   every transition and timeout defined</text>')
add(f'<line x1="34" y1="72" x2="{W-34}" y2="72" stroke="#000" stroke-width="1"/>')

X, BW, BH = 120, 250, 96
ys = [100, 232, 364, 496, 628, 760]
states = [
 ("IDLE",      ["all outputs off","both valves closed"]),
 ("FILL",      ["XV-101 open, duty pump on","fixed flow 30 m3/h","heater off, dosing off"]),
 ("HEAT",      ["cascade on, level 1800 mm","heater on, dosing on"]),
 ("HOLD",      ["hold level, temp, dosing","residence timer running"]),
 ("DISCHARGE", ["heater off, dosing off","XV-102 open, P-102 at 60%"]),
 ("DRAIN",     ["P-102 at 100%","empty the tank"]),
]
conds = [
 "Start pressed  AND  no trip  AND  LT-101 above 400 mm",
 "LT-102 reaches 1200 mm",
 "TT-102 within 0.5 degC of setpoint for 60 s continuous",
 "residence timer reaches 600 s",
 "LT-102 falls to 300 mm",
]
tmo = ["", "timeout 900 s", "timeout 5400 s", "", "timeout 600 s", ""]
for (t,l),y in zip(states,ys):
    box(X,y,BW,BH,t,l)
for i,c in enumerate(conds):
    arr(X+BW/2, ys[i]+BH, X+BW/2, ys[i+1])
    add(f'<text x="{X+BW+18}" y="{ys[i]+BH+27}" class="cd" text-anchor="start" style="text-anchor:start">{c}</text>')
for i,t in enumerate(tmo):
    if t: add(f'<text x="{X+BW-8}" y="{ys[i]+BH-8}" class="nt" style="text-anchor:end;font-style:italic">{t}</text>')

# loop back
add(f'<path d="M {X} {ys[5]+BH/2} L 62 {ys[5]+BH/2} L 62 {ys[0]+BH/2} L {X} {ys[0]+BH/2}" stroke="#000" stroke-width="1.8" fill="none" marker-end="url(#a)"/>')
add(f'<text x="{X+BW/2}" y="{ys[5]+BH+26}" class="cd">LT-102 below 50 mm for 10 s, then back to IDLE</text>')

# TRIP
box(1010, 300, 250, 110, "TRIP", ["all pumps off, heater off","both valves closed","LATCHED"], fill="#f7f7f7")
add('<text x="1135" y="432" class="nt" style="text-anchor:middle;font-style:italic">entered from ANY state</text>')
RAIL = 880
for y in (ys[1]+BH/2, ys[2]+BH/2, ys[3]+BH/2):
    add(f'<path d="M {X+BW} {y} L {RAIL} {y}" stroke="#000" stroke-width="1.2" stroke-dasharray="5,4" fill="none"/>')
add(f'<path d="M {RAIL} {ys[1]+BH/2} L {RAIL} {ys[3]+BH/2}" stroke="#000" stroke-width="1.2" stroke-dasharray="5,4" fill="none"/>')
add(f'<path d="M {RAIL} 355 L 1010 355" stroke="#000" stroke-width="1.2" stroke-dasharray="5,4" fill="none" marker-end="url(#a)"/>')
add(f'<text x="{RAIL+66}" y="345" class="cd">any interlock</text>')
arr(1135, 300, 1135, 250)
add('<text x="1145" y="240" class="nt" style="text-anchor:start">to IDLE only when the cause has cleared AND operator presses Reset</text>')

# notes
NY = 600
add(f'<rect x="1010" y="{NY}" width="440" height="250" fill="none" stroke="#000" stroke-width="1.2"/>')
add(f'<line x1="1010" y1="{NY+22}" x2="1450" y2="{NY+22}" stroke="#000" stroke-width="1.2"/>')
add(f'<text x="1020" y="{NY+15}" class="ntb">DESIGN NOTES</text>')
notes = [
 ("Fixed flow during FILL", "there is no level worth controlling"),
 ("", "until the tank has something in it"),
 ("60 s stable before HOLD", "stops a momentary excursion through"),
 ("", "setpoint advancing a stratified tank"),
 ("10 s confirm before IDLE", "a splash as the last liquid clears"),
 ("", "the tapping must not end the batch"),
 ("Timeouts 2 to 3x expected", "too tight nuisance trips, too loose"),
 ("", "hides a real fault for far too long"),
 ("Stop order on abort", "heater, dosing, pumps, valves."),
 ("", "The heater is never left on in a tank"),
 ("", "that is being emptied."),
]
for i,(a,b) in enumerate(notes):
    y = NY+42+i*19
    if a: add(f'<text x="1020" y="{y}" class="ntb">{a}</text>')
    add(f'<text x="{1020 if not a else 1190}" y="{y}" class="nt">{b}</text>')

add('</svg>')
HERE = pathlib.Path(__file__).resolve().parent
HERE = HERE.parent / 'drawings'   # drawings live in drawings/
(HERE/"sequence_diagram.svg").write_text("\n".join(P))
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if pathlib.Path(CH).exists():
    w=HERE/"_s.html"; w.write_text(f'<html><body style="margin:0"><img src="sequence_diagram.svg" width="{W}"></body></html>')
    subprocess.run([CH,"--headless","--disable-gpu",f"--screenshot={HERE/'sequence_diagram.png'}",
                    f"--window-size={W},{H}","--default-background-color=FFFFFFFF",f"file://{w}"],
                   capture_output=True,timeout=120)
    w.unlink()
print("wrote sequence_diagram.svg and sequence_diagram.png")
