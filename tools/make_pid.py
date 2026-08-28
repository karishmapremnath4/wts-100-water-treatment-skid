#!/usr/bin/env python3
"""WTS-100 Piping and Instrumentation Diagram, ISA-5.1 symbology.

Run:  python3 make_pid.py

Writes pid.svg and pid.png beside this script. The PNG uses Google Chrome
headless to rasterise the SVG. Without Chrome you still get the SVG, which
opens in any browser and scales without blurring.

Layout notes, so edits do not break the drawing:
  - CSS in the <style> block overrides text-anchor attributes on elements,
    so alignment is set with classes (.tag centred, .noteL left) not attributes.
  - Instrument bubbles must not sit inside a vessel rectangle or they vanish
    behind it. Vessels: T-101 (70,250,150,210), T-102 (700,300,230,250),
    T-103 (700,690,110,130).
  - The chemical injection riser runs at x=1360 and the discharge line at
    y=590 so the two never share a vertical and read as one pipe.
"""
import pathlib, subprocess

HERE = pathlib.Path(__file__).resolve().parent
HERE = HERE.parent / 'drawings'   # drawings live in drawings/
W, H = 1640, 1010
OX, OY = 34, 52          # content offset inside the drawing frame
P = []
def add(s): P.append(s)

def bubble(cx, cy, top, bot, shared=False, r=25):
    """ISA instrument bubble. shared=True draws a square behind it (control room)."""
    if shared:
        add(f'<rect x="{cx-r}" y="{cy-r}" width="{2*r}" height="{2*r}" fill="#fff" stroke="#000" stroke-width="1.6"/>')
    add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="#000" stroke-width="1.6"/>')
    add(f'<line x1="{cx-r}" y1="{cy}" x2="{cx+r}" y2="{cy}" stroke="#000" stroke-width="1"/>')
    add(f'<text x="{cx}" y="{cy-6}" class="tag">{top}</text>')
    add(f'<text x="{cx}" y="{cy+16}" class="tag">{bot}</text>')

def vessel(x, y, w, h, tag, name, lx=None):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#000" stroke-width="2"/>')
    add(f'<text x="{lx or x+w/2}" y="{y-24}" class="eqtag">{tag}</text>')
    add(f'<text x="{lx or x+w/2}" y="{y-8}" class="eqname">{name}</text>')

def liquid(*a, **k):
    pass          # engineering drawings do not shade liquid levels

def pump(cx, cy, tag, name):
    add(f'<circle cx="{cx}" cy="{cy}" r="24" fill="#fff" stroke="#000" stroke-width="2"/>')
    add(f'<polygon points="{cx-10},{cy-13} {cx-10},{cy+13} {cx+15},{cy}" fill="#000"/>')
    add(f'<text x="{cx}" y="{cy+42}" class="eqtag">{tag}</text>')
    add(f'<text x="{cx}" y="{cy+56}" class="eqname">{name}</text>')

def valve(cx, cy, tag, control=False):
    add(f'<polygon points="{cx-16},{cy-13} {cx-16},{cy+13} {cx+16},{cy-13} {cx+16},{cy+13}" fill="#fff" stroke="#000" stroke-width="2"/>')
    if control:
        add(f'<path d="M {cx-13} {cy-16} Q {cx} {cy-34} {cx+13} {cy-16} Z" fill="#fff" stroke="#000" stroke-width="1.6"/>')
        add(f'<line x1="{cx}" y1="{cy-16}" x2="{cx}" y2="{cy-25}" stroke="#000" stroke-width="1.6"/>')
    add(f'<text x="{cx}" y="{cy+34}" class="eqtag">{tag}</text>')

def hvalve(cx, cy, tag=None, vert=False):
    """Manual block valve, small bowtie."""
    if vert:
        pts = f"{cx-10},{cy-9} {cx+10},{cy-9} {cx-10},{cy+9} {cx+10},{cy+9}"
    else:
        pts = f"{cx-9},{cy-10} {cx-9},{cy+10} {cx+9},{cy-10} {cx+9},{cy+10}"
    add(f'<polygon points="{pts}" fill="#fff" stroke="#000" stroke-width="1.6"/>')
    if tag:
        add(f'<text x="{cx}" y="{cy+26}" class="vtag">{tag}</text>')

def checkv(cx, cy, tag=None):
    """Non return valve: bowtie with a flap bar. Flow left to right."""
    add(f'<polygon points="{cx-9},{cy-10} {cx-9},{cy+10} {cx+9},{cy-10} {cx+9},{cy+10}" '
        f'fill="#fff" stroke="#000" stroke-width="1.6"/>')
    add(f'<line x1="{cx+9}" y1="{cy-12}" x2="{cx+9}" y2="{cy+12}" stroke="#000" stroke-width="2"/>')
    if tag:
        add(f'<text x="{cx}" y="{cy-18}" class="vtag">{tag}</text>')

def relief(cx, cy, tag):
    """Pressure relief valve, angle body with spring."""
    add(f'<polygon points="{cx-10},{cy+10} {cx+10},{cy+10} {cx-10},{cy-8} {cx+10},{cy-8}" '
        f'fill="#fff" stroke="#000" stroke-width="1.6"/>')
    add(f'<path d="M {cx} {cy-8} l -6 -5 l 12 -5 l -12 -5 l 12 -5" fill="none" stroke="#000" stroke-width="1.6"/>')
    add(f'<text x="{cx+16}" y="{cy-2}" class="vtagL">{tag}</text>')

def pline(pts, arrow=True):
    d = " ".join(f"{'M' if i==0 else 'L'} {x} {y}" for i,(x,y) in enumerate(pts))
    mk = ' marker-end="url(#ar)"' if arrow else ""
    add(f'<path d="{d}" fill="none" stroke="#000" stroke-width="2.6"{mk}/>')

def sline(pts):
    d = " ".join(f"{'M' if i==0 else 'L'} {x} {y}" for i,(x,y) in enumerate(pts))
    add(f'<path d="{d}" fill="none" stroke="#000" stroke-width="1" stroke-dasharray="6,4"/>')

add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
add('''<defs>
<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
  <path d="M 0 0 L 10 5 L 0 10 z" fill="#000"/></marker>
<style>
  text  { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; text-anchor: middle; fill:#000; }
  .tag  { font-size: 12px; font-weight: 600; letter-spacing: .3px; }
  .eqtag{ font-size: 12.5px; font-weight: 700; letter-spacing: .4px; }
  .eqname{font-size: 10px; }
  .noteL{ font-size: 10.5px; text-anchor: start; }
  .vtag { font-size: 9.5px; font-weight: 600; }
  .vtagL{ font-size: 9.5px; font-weight: 600; text-anchor: start; }
  .line { font-size: 9.5px; font-weight: 600; }
  .grid { font-size: 11px; font-weight: 700; }
  .tbL  { font-size: 9px; text-anchor: start; letter-spacing:.4px; }
  .tbV  { font-size: 11.5px; font-weight: 700; text-anchor: start; }
  .tbT  { font-size: 15px; font-weight: 700; text-anchor: start; letter-spacing:.4px; }
  .nt   { font-size: 9.5px; text-anchor: start; }
  .ntb  { font-size: 10px; font-weight: 700; text-anchor: start; }
  .ttl  { font-size: 21px; font-weight: 700; text-anchor: start; }
  .sub  { font-size: 12.5px; fill:#444; text-anchor: start; }
  .hdr  { font-size: 12px; font-weight:700; text-anchor: start; fill:#111; }
</style>
</defs>''')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
add(f'<g transform="translate({OX},{OY})">')

# controllers, control room row
CY = 78
bubble(470, CY, "FIC", "101", shared=True)
bubble(770, CY, "LIC", "102", shared=True)
bubble(980, CY, "TIC", "102", shared=True)
bubble(1180, CY, "FFIC", "103", shared=True)
add(f'<line x1="120" y1="{CY+52}" x2="1440" y2="{CY+52}" stroke="#999" stroke-width="1" stroke-dasharray="3,4"/>')
add(f'<text x="126" y="{CY+46}" class="hdr">CONTROL ROOM</text>')
add(f'<text x="126" y="{CY+68}" class="hdr">FIELD</text>')

# T-101
vessel(70, 250, 150, 210, "T-101", "Raw Water Tank", lx=178)
liquid(70, 250, 150, 210, 0.62)
# top mounted radar: bubble sits over the tank, signal lands on the roof
bubble(110, 178, "LT", "101", r=23); sline([(110,201),(110,250)])
# side mounted fork switch: lands on the tank wall near the bottom
bubble(45, 490, "LSLL", "101", r=23); sline([(45,467),(45,430),(70,430)])

pline([(220,360),(245,360)], arrow=False)
pline([(245,360),(245,300),(300,300)], arrow=False)
pline([(245,360),(245,420),(300,420)], arrow=False)
# suction block valves, so a pump can be isolated for maintenance
hvalve(270, 300, "V-101A")
hvalve(270, 420, "V-101B")
pump(324, 300, "P-101A", "Raw Water Duty")
pump(324, 420, "P-101B", "Raw Water Standby")
# non return valves stop the running pump pushing back through the idle one
checkv(370, 300, "NRV-101A")
checkv(370, 420, "NRV-101B")
hvalve(400, 300, "V-102A")
hvalve(400, 420, "V-102B")
pline([(348,300),(420,300),(420,360)], arrow=False)
pline([(348,420),(420,420),(420,360)], arrow=False)
pline([(420,360),(430,360)], arrow=False)
bubble(392, 214, "PT", "101", r=23); sline([(392,237),(392,300)])

# flow element + valves
add('<rect x="430" y="345" width="30" height="30" fill="#fff" stroke="#000" stroke-width="2"/>')
add('<text x="445" y="366" class="eqtag">M</text>')
bubble(445, 214, "FT", "101", r=23); sline([(445,237),(445,345)])
pline([(460,360),(540,360)], arrow=False)
valve(556, 360, "FCV-101", control=True)
pline([(572,360),(640,360)], arrow=False)
valve(656, 360, "XV-101")
# solenoid above the valve, position switches below where there is clear space
add('<rect x="644" y="316" width="24" height="18" fill="#fff" stroke="#000" stroke-width="1.6"/>')
add('<text x="656" y="330" class="tag">S</text>')
bubble(580, 452, "ZSO", "101", r=20); sline([(580,432),(580,404),(644,404),(644,374)])
bubble(660, 452, "ZSC", "101", r=20); sline([(660,432),(660,374)])
sline([(656,316),(656,276)])
pline([(672,360),(760,360),(760,300)], arrow=True)

# T-102
vessel(700, 300, 230, 250, "T-102", "Treatment Tank", lx=825)
liquid(700, 300, 230, 250, 0.60)
add('<path d="M 730 500 L 730 470 L 760 470 L 760 500 L 790 500 L 790 470 L 820 470" fill="none" stroke="#000" stroke-width="2.5"/>')
add('<text x="775" y="522" class="eqtag">HTR-101</text>')
add('<text x="775" y="535" class="eqname">6 kW Immersion</text>')
for cy,(t,b) in zip([330,400,470,540], [("LSHH","102"),("LT","102"),("TT","102"),("TSHH","102")]):
    bubble(960, cy, t, b, r=23); sline([(937,cy),(930,cy)])

# T-102 is a closed vessel with a 6 kW heater, so it needs overpressure protection
pline([(715,300),(715,278)], arrow=False)
relief(715, 268, "PSV-102")
pline([(715,250),(715,226)], arrow=True)
add('<text x="723" y="230" class="noteL">NOTE 3</text>')

# chemical dosing
vessel(700, 626, 110, 130, "T-103", "Chemical")
liquid(700, 626, 110, 130, 0.55)
pline([(810,696),(860,696)], arrow=False)
pump(884, 696, "P-103", "Dosing Pump")
pline([(908,696),(960,696)], arrow=False)
add('<rect x="960" y="681" width="30" height="30" fill="#fff" stroke="#000" stroke-width="2"/>')
add('<text x="975" y="702" class="eqtag">C</text>')
bubble(1060, 696, "FT", "103", r=23); sline([(1037,696),(990,696)])
pline([(990,696),(1360,696),(1360,240),(890,240),(890,300)], arrow=True)

# discharge
add('<path d="M 880 550 L 880 590 L 1010 590" fill="none" stroke="#000" stroke-width="2.6"/>')
valve(1026, 590, "XV-102")
add('<rect x="1014" y="546" width="24" height="18" fill="#fff" stroke="#000" stroke-width="1.6"/>')
add('<text x="1026" y="560" class="tag">S</text>')
sline([(1026,546),(1026,520)])
pline([(1042,590),(1090,590)], arrow=False)
pump(1114, 590, "P-102", "Discharge Pump")
sline([(1114,566),(1114,520)])
pline([(1138,590),(1250,590)], arrow=True)
add('<text x="1196" y="572" class="eqtag">TO STORAGE</text>')
bubble(1160, 470, "AT", "102", r=23); sline([(1160,493),(1160,590)])

# signal wiring
sline([(445,191),(445,150),(470,150),(470,103)])
sline([(470,53),(470,30),(556,30),(556,326)])
sline([(960,377),(1010,377),(1010,150),(770,150),(770,103)])
sline([(770,53),(770,20),(430,20),(430,150),(452,150)])
sline([(960,447),(1040,447),(1040,140),(980,140),(980,103)])
sline([(980,53),(1000,53),(1000,40),(880,40),(880,455),(820,455),(820,470)])
sline([(1060,673),(1060,636),(1180,636),(1180,103)])
sline([(1180,53),(1320,53),(1320,616),(884,616),(884,672)])
sline([(1160,447),(1160,300),(1236,300)])
add('<text x="1244" y="304" class="noteL">NOTE 4</text>')
# FT-101 also feeds the ratio controller: dose setpoint = water flow x ratio
sline([(445,168),(1128,168),(1128,78),(1155,78)])
add('<circle cx="445" cy="168" r="2.6" fill="#000"/>')

# line numbers: size, service, sequence
add('<text x="262" y="344" class="line">50-WA-101</text>')
add('<text x="500" y="343" class="line">50-WA-102</text>')
add('<text x="945" y="573" class="line">50-WA-103</text>')
add('<text x="925" y="677" class="line">15-CH-101</text>')

add('</g>')          # end content group

# ---- drawing frame and grid references ------------------------------------
add(f'<rect x="12" y="12" width="{W-24}" height="{H-24}" fill="none" stroke="#000" stroke-width="1"/>')
add(f'<rect x="30" y="30" width="{W-60}" height="{H-60}" fill="none" stroke="#000" stroke-width="1.8"/>')

COLS, ROWS = 8, 5
cw = (W - 60) / COLS
for i in range(COLS):
    cx = 30 + cw * (i + 0.5)
    add(f'<text x="{cx}" y="26" class="grid">{i+1}</text>')
    add(f'<text x="{cx}" y="{H-16}" class="grid">{i+1}</text>')
    if i:
        x = 30 + cw * i
        add(f'<line x1="{x}" y1="12" x2="{x}" y2="30" stroke="#000" stroke-width="1"/>')
        add(f'<line x1="{x}" y1="{H-30}" x2="{x}" y2="{H-12}" stroke="#000" stroke-width="1"/>')
rh = (H - 60) / ROWS
for i in range(ROWS):
    cy = 30 + rh * (i + 0.5)
    add(f'<text x="21" y="{cy+4}" class="grid">{chr(65+i)}</text>')
    add(f'<text x="{W-21}" y="{cy+4}" class="grid">{chr(65+i)}</text>')
    if i:
        y = 30 + rh * i
        add(f'<line x1="12" y1="{y}" x2="30" y2="{y}" stroke="#000" stroke-width="1"/>')
        add(f'<line x1="{W-30}" y1="{y}" x2="{W-12}" y2="{y}" stroke="#000" stroke-width="1"/>')

# ---- notes -----------------------------------------------------------------
NX, NY, NW, NH = 40, 856, 520, 122
add(f'<rect x="{NX}" y="{NY}" width="{NW}" height="{NH}" fill="none" stroke="#000" stroke-width="1.4"/>')
add(f'<line x1="{NX}" y1="{NY+20}" x2="{NX+NW}" y2="{NY+20}" stroke="#000" stroke-width="1.4"/>')
add(f'<text x="{NX+8}" y="{NY+14}" class="ntb">NOTES</text>')
notes = [
 "1.  ALL INSTRUMENTS 4-20 mA UNLESS NOTED.",
 "2.  SAFETY CONTACTS WIRED NORMALLY CLOSED. DE-ENERGISE TO TRIP.",
 "3.  PSV-102 DISCHARGE TO SAFE LOCATION.",
 "4.  AT-102 SIGNAL TO HISTORIAN.",
 "5.  DRAWING SCOPED TO CONTROL SYSTEM. INSTRUMENT ROOT VALVES,",
 "     DRAINS AND PIPE SPECIFICATIONS NOT SHOWN.",
]
for i, n in enumerate(notes):
    add(f'<text x="{NX+8}" y="{NY+36+i*16}" class="nt">{n}</text>')

# ---- legend ----------------------------------------------------------------
LX, LY, LW, LH = 578, 856, 500, 122
add(f'<rect x="{LX}" y="{LY}" width="{LW}" height="{LH}" fill="none" stroke="#000" stroke-width="1.4"/>')
add(f'<line x1="{LX}" y1="{LY+20}" x2="{LX+LW}" y2="{LY+20}" stroke="#000" stroke-width="1.4"/>')
add(f'<text x="{LX+8}" y="{LY+14}" class="ntb">LEGEND</text>')
add(f'<line x1="{LX+14}" y1="{LY+40}" x2="{LX+70}" y2="{LY+40}" stroke="#000" stroke-width="2.6"/>')
add(f'<text x="{LX+80}" y="{LY+44}" class="nt">PROCESS LINE</text>')
add(f'<line x1="{LX+14}" y1="{LY+62}" x2="{LX+70}" y2="{LY+62}" stroke="#000" stroke-width="1" stroke-dasharray="6,4"/>')
add(f'<text x="{LX+80}" y="{LY+66}" class="nt">ELECTRICAL SIGNAL</text>')
add(f'<circle cx="{LX+42}" cy="{LY+90}" r="13" fill="#fff" stroke="#000" stroke-width="1.6"/>')
add(f'<line x1="{LX+29}" y1="{LY+90}" x2="{LX+55}" y2="{LY+90}" stroke="#000" stroke-width="1"/>')
add(f'<text x="{LX+80}" y="{LY+86}" class="nt">FIELD MOUNTED INSTRUMENT</text>')
add(f'<rect x="{LX+245}" y="{LY+77}" width="26" height="26" fill="#fff" stroke="#000" stroke-width="1.6"/>')
add(f'<circle cx="{LX+258}" cy="{LY+90}" r="13" fill="#fff" stroke="#000" stroke-width="1.6"/>')
add(f'<line x1="{LX+245}" y1="{LY+90}" x2="{LX+271}" y2="{LY+90}" stroke="#000" stroke-width="1"/>')
add(f'<text x="{LX+296}" y="{LY+86}" class="nt">CONTROL ROOM</text>')
add(f'<text x="{LX+296}" y="{LY+98}" class="nt">SHARED DISPLAY</text>')
add(f'<text x="{LX+14}" y="{LY+116}" class="nt">S = SOLENOID      M = MAGNETIC FLOWMETER      C = CORIOLIS FLOWMETER</text>')

# ---- title block -----------------------------------------------------------
TX, TY, TW, TH = 1096, 856, 504, 122
add(f'<rect x="{TX}" y="{TY}" width="{TW}" height="{TH}" fill="none" stroke="#000" stroke-width="1.8"/>')
for yy in (TY+42, TY+72, TY+97):
    add(f'<line x1="{TX}" y1="{yy}" x2="{TX+TW}" y2="{yy}" stroke="#000" stroke-width="1"/>')
add(f'<line x1="{TX+300}" y1="{TY+72}" x2="{TX+300}" y2="{TY+TH}" stroke="#000" stroke-width="1"/>')
add(f'<line x1="{TX+400}" y1="{TY+72}" x2="{TX+400}" y2="{TY+TH}" stroke="#000" stroke-width="1"/>')
add(f'<line x1="{TX+150}" y1="{TY+97}" x2="{TX+150}" y2="{TY+TH}" stroke="#000" stroke-width="1"/>')

add(f'<text x="{TX+10}" y="{TY+20}" class="tbL">PROJECT</text>')
add(f'<text x="{TX+10}" y="{TY+36}" class="tbT">WTS-100  WATER TREATMENT AND TRANSFER SKID</text>')
add(f'<text x="{TX+10}" y="{TY+56}" class="tbL">TITLE</text>')
add(f'<text x="{TX+70}" y="{TY+57}" class="tbV">PIPING AND INSTRUMENTATION DIAGRAM</text>')
add(f'<text x="{TX+10}" y="{TY+84}" class="tbL">DRAWING No</text>')
add(f'<text x="{TX+10}" y="{TY+94}" class="tbV">WTS-100-PID-001</text>')
add(f'<text x="{TX+310}" y="{TY+84}" class="tbL">REV</text>')
add(f'<text x="{TX+310}" y="{TY+94}" class="tbV">A</text>')
add(f'<text x="{TX+410}" y="{TY+84}" class="tbL">SHEET</text>')
add(f'<text x="{TX+410}" y="{TY+94}" class="tbV">1 OF 1</text>')
add(f'<text x="{TX+10}" y="{TY+110}" class="tbL">DRAWN</text>')
add(f'<text x="{TX+60}" y="{TY+111}" class="tbV">K. PREMNATH</text>')
add(f'<text x="{TX+160}" y="{TY+110}" class="tbL">CHECKED</text>')
add(f'<text x="{TX+310}" y="{TY+110}" class="tbL">SCALE</text>')
add(f'<text x="{TX+350}" y="{TY+111}" class="tbV">NTS</text>')
add(f'<text x="{TX+410}" y="{TY+110}" class="tbL">DATE</text>')
add(f'<text x="{TX+445}" y="{TY+111}" class="tbV">AUG 2026</text>')

add('</svg>')

svg_path = HERE / "pid.svg"
svg_path.write_text("\n".join(P))
print(f"wrote {svg_path.name}, {len(P)} elements")

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if pathlib.Path(CHROME).exists():
    wrap = HERE / "_pid.html"
    wrap.write_text('<html><body style="margin:0">'
                    f'<img src="{svg_path.name}" width="{W}"></body></html>')
    subprocess.run([CHROME, "--headless", "--disable-gpu",
                    f"--screenshot={HERE / 'pid.png'}",
                    f"--window-size={W},{H}",
                    "--default-background-color=FFFFFFFF",
                    f"file://{wrap}"], capture_output=True, timeout=120)
    wrap.unlink()
    print("wrote pid.png")
else:
    print("Chrome not found, PNG skipped. Open pid.svg in a browser.")
