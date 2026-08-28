#!/usr/bin/env python3
"""WTS-100 ladder logic drawings, IEC 61131-3 Ladder Diagram.

Writes ladder_safety.svg/.png and ladder_pumps.svg/.png beside this script.

Symbols
    --] [--   normally open contact,   passes power when the tag is TRUE
    --]/[--   normally closed contact, passes power when the tag is FALSE
    --( )--   coil,  (L) latch,  (U) unlatch
    [ TON ]   on delay timer

Rungs are built as a list of series elements. Parallel branches are given as
extra rows, which is how an OR is drawn. The coil is always at COIL_X and the
connecting wire is drawn automatically, so a rung can never be left open.
"""
import pathlib, subprocess

P = []
def add(s): P.append(s)

LX, RX = 96, 1500
CW     = 148
COIL_X = 1180

def header(W, H, title, sub):
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    add('''<defs><style>
      text { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; text-anchor: middle; fill:#000; }
      .tag  { font-size: 10.5px; font-weight: 600; }
      .desc { font-size: 8.5px; }
      .rung { font-size: 11px; font-weight: 700; text-anchor: end; }
      .note { font-size: 9.5px; text-anchor: start; font-style: italic; }
      .h1   { font-size: 16px; font-weight: 700; text-anchor: start; letter-spacing:.4px; }
      .h2   { font-size: 9.5px; text-anchor: start; }
      .cmt  { font-size: 9.5px; text-anchor: start; font-weight: 600; }
    </style></defs>''')
    add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
    add(f'<rect x="12" y="12" width="{W-24}" height="{H-24}" fill="none" stroke="#000" stroke-width="1"/>')
    add(f'<text x="30" y="40" class="h1">{title}</text>')
    add(f'<text x="30" y="57" class="h2">{sub}</text>')
    add(f'<line x1="30" y1="66" x2="{W-30}" y2="66" stroke="#000" stroke-width="1"/>')

def wire(x1, y1, x2, y2):
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#000" stroke-width="1.6"/>')

def _contact(x, y, tag, desc, nc):
    add(f'<line x1="{x-13}" y1="{y-13}" x2="{x-13}" y2="{y+13}" stroke="#000" stroke-width="2.2"/>')
    add(f'<line x1="{x+13}" y1="{y-13}" x2="{x+13}" y2="{y+13}" stroke="#000" stroke-width="2.2"/>')
    if nc:
        add(f'<line x1="{x-16}" y1="{y+14}" x2="{x+16}" y2="{y-14}" stroke="#000" stroke-width="2"/>')
    add(f'<text x="{x}" y="{y-20}" class="tag">{tag}</text>')
    if desc: add(f'<text x="{x}" y="{y+27}" class="desc">{desc}</text>')

def _timer(x, y, tag, pt):
    w, h = 108, 50
    add(f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" fill="#fff" stroke="#000" stroke-width="1.8"/>')
    add(f'<text x="{x}" y="{y-h/2+15}" class="tag">TON</text>')
    add(f'<text x="{x}" y="{y+2}" class="desc">{tag}</text>')
    add(f'<text x="{x}" y="{y+14}" class="desc">PT {pt}</text>')
    return w/2

def series(y, elems, x0=None):
    """Draw a series chain from x0 (default the left rail). Returns the x it ends at."""
    x = LX if x0 is None else x0
    for e in elems:
        cx = x + CW/2
        if e[0] == "T":
            half = _timer(cx, y, e[1], e[2])
            wire(x, y, cx-half, y); wire(cx+half, y, x+CW, y)
        else:
            wire(x, y, cx-13, y)
            _contact(cx, y, e[1], e[2] if len(e) > 2 else "", e[0] == "NC")
            wire(cx+13, y, x+CW, y)
        x += CW
    return x

def coil(y, tag, desc="", kind="", x_from=None):
    if x_from is not None:
        wire(x_from, y, COIL_X-17, y)
    add(f'<path d="M {COIL_X-17} {y-14} A 18 18 0 0 0 {COIL_X-17} {y+14}" fill="none" stroke="#000" stroke-width="2.2"/>')
    add(f'<path d="M {COIL_X+17} {y-14} A 18 18 0 0 1 {COIL_X+17} {y+14}" fill="none" stroke="#000" stroke-width="2.2"/>')
    if kind: add(f'<text x="{COIL_X}" y="{y+5}" class="tag">{kind}</text>')
    wire(COIL_X+17, y, RX, y)
    add(f'<text x="{COIL_X}" y="{y-20}" class="tag">{tag}</text>')
    if desc: add(f'<text x="{COIL_X}" y="{y+27}" class="desc">{desc}</text>')

def rung(y, n, cmt, main, out, branches=None, gap=58, tail=None):
    """main + branches form a parallel (OR) block. tail is drawn in series AFTER it.

    A seal-in must parallel ONLY the start contact, with stop and permissives
    in series after the block. Putting them inside the block would let the
    seal-in bypass the stop button.
    """
    add(f'<text x="30" y="{y-40}" class="cmt">RUNG {n}   {cmt}</text>')
    add(f'<text x="{LX-14}" y="{y+4}" class="rung">{n}</text>')
    # block is as wide as its WIDEST row, else a long branch runs past the join
    width = max([len(main)] + [len(b) for b in (branches or [])])
    end   = LX + CW*width
    bend  = series(y, main)
    if bend < end: wire(bend, y, end, y)
    if branches:
        ybot = y + gap*len(branches)
        wire(LX, y, LX, ybot)                       # left side of the block
        wire(end, y, end, ybot)                     # right side, at the widest row
        for i, b in enumerate(branches):
            by = y + gap*(i+1)
            bx = series(by, b)
            if bx < end: wire(bx, by, end, by)      # pad shorter branches to the join
    if tail:
        end = series(y, tail, x0=end)               # in series, outside the block
    coil(y, out[0], out[1] if len(out) > 1 else "", out[2] if len(out) > 2 else "", x_from=end)

def rails(y0, y1):
    add(f'<line x1="{LX}" y1="{y0}" x2="{LX}" y2="{y1}" stroke="#000" stroke-width="2.5"/>')
    add(f'<line x1="{RX}" y1="{y0}" x2="{RX}" y2="{y1}" stroke="#000" stroke-width="2.5"/>')

def footer(W, H, text):
    add(f'<text x="30" y="{H-24}" class="note">{text}</text>')
    add('</svg>')

def save(name, W, H):
    HERE = pathlib.Path(__file__).resolve().parent.parent / 'drawings'   # drawings live in drawings/
    (HERE/f"{name}.svg").write_text("\n".join(P))
    print(f"wrote {name}.svg")
    CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if pathlib.Path(CHROME).exists():
        wrap = HERE/f"_{name}.html"
        wrap.write_text(f'<html><body style="margin:0"><img src="{name}.svg" width="{W}"></body></html>')
        subprocess.run([CHROME,"--headless","--disable-gpu",f"--screenshot={HERE/(name+'.png')}",
                        f"--window-size={W},{H}","--default-background-color=FFFFFFFF",
                        f"file://{wrap}"], capture_output=True, timeout=120)
        wrap.unlink(); print(f"wrote {name}.png")

# ============================================================ POU_SAFETY
W, H = 1560, 980
P.clear()
header(W, H, "POU_SAFETY   Interlocks and Permissives",
       "WTS-100 Water Treatment and Transfer Skid   |   IEC 61131-3 Ladder Diagram   |   Executed first every scan")
rails(90, 910)

# Rung 1: the four trip causes are alternatives, so they are PARALLEL not series.
rung(150, 1,
     "trip causes.  Any one of these trips.  Safety contacts are wired normally closed, so healthy = TRUE.",
     [("NC","ESD_01_OK","emergency stop pressed")],
     ("TRIP_CAUSE","a trip condition is present"),
     branches=[
        [("NC","TSHH_102_OK","over temperature")],
        [("NC","XA_101A_OK","pump A overload"), ("NC","XA_101B_OK","pump B overload")],
        [("NO","AIN_FAULT","analog invalid over 30 s")],
     ])
add(f'<text x="{LX+CW*2.6}" y="{150+58*2+4}" class="note">these two are in series, so ONE failed pump does not trip</text>')

rung(420, 2, "trip latch, with seal in.",
     [("NO","TRIP_CAUSE","")],
     ("TRIP","latched until reset","L"),
     branches=[[("NO","TRIP","seal in")]])

rung(560, 3, "reset.  Unlatches only when the cause has already cleared.",
     [("NO","HS_04_RESET","reset pushbutton"), ("NC","TRIP_CAUSE","no cause present")],
     ("TRIP","","U"))

rung(670, 4, "permission to run the raw water pumps.  I2 dry run, I3 overfill.",
     [("NO","ESD_01_OK",""), ("NO","LSLL_101_OK","raw tank not empty"),
      ("NO","LSHH_102_OK","treat tank not full"), ("NC","TRIP","")],
     ("PERM_RAW_PUMPS",""))

rung(770, 5, "permission to run the heater.  I4 over temperature, I5 low level.",
     [("NO","ESD_01_OK",""), ("NO","TSHH_102_OK",""), ("NO","LT_102_VALID","level reading good"),
      ("NO","TT_102_VALID","temp reading good"), ("NO","LVL_ABOVE_800","level over 800 mm"),
      ("NC","TRIP","")],
     ("PERM_HEATER",""))

rung(870, 6, "permission to open the inlet.  I3 overfill.",
     [("NO","ESD_01_OK",""), ("NO","LSHH_102_OK",""), ("NC","TRIP","")],
     ("PERM_INLET",""))

footer(W, H, "POU_SAFETY issues permissions only.  It never commands a device.  Every other POU must pass "
             "through these permissions, so a defect in the sequence cannot fire the heater in an empty tank.")
save("ladder_safety", W, H)

# ============================================================ POU_PUMPS
W, H = 1560, 940
P.clear()
header(W, H, "POU_PUMPS   Duty and Standby Raw Water Pumps",
       "WTS-100 Water Treatment and Transfer Skid   |   IEC 61131-3 Ladder Diagram")
rails(90, 880)

rung(150, 1, "start and stop with seal in.  The seal in parallels START ONLY, so STOP and the "
     "safety permission stay in series and can always break the rung.",
     [("NO","HS_02_START","start pushbutton")],
     ("RUN_REQ","pumps requested to run"),
     branches=[[("NO","RUN_REQ","seal in")]],
     tail=[("NC","HS_03_STOP","stop, wired NC"), ("NO","PERM_RAW_PUMPS","from POU_SAFETY")])

rung(310, 2, "duty pump A runs when A is selected and healthy.",
     [("NO","RUN_REQ",""), ("NO","DUTY_IS_A","A selected as duty"), ("NC","FAULT_A","A healthy")],
     ("MTR_101A","pump A contactor"))

rung(420, 3, "standby pump B runs if B is duty, or if A has faulted.",
     [("NO","RUN_REQ",""), ("NC","DUTY_IS_A","B is duty"), ("NC","FAULT_B","B healthy")],
     ("MTR_101B","pump B contactor"),
     branches=[[("NO","RUN_REQ",""), ("NO","FAULT_A","A has failed"), ("NC","FAULT_B","")]])

rung(590, 4, "pump A fault.  Commanded on but no run feedback within 3 seconds.",
     [("NO","MTR_101A","commanded on"), ("NC","XS_101A","no run feedback"), ("T","T_FAULT_A","3 s")],
     ("FAULT_A","latched","L"))

rung(700, 5, "pump B fault.  The same test on the other pump.",
     [("NO","MTR_101B","commanded on"), ("NC","XS_101B","no run feedback"), ("T","T_FAULT_B","3 s")],
     ("FAULT_B","latched","U" if False else "L"))

rung(810, 6, "both pumps failed.  This is interlock I6 and it trips the plant.",
     [("NO","FAULT_A",""), ("NO","FAULT_B","")],
     ("BOTH_PUMPS_FAILED","to POU_SAFETY rung 1"))

footer(W, H, "Duty alternates on each completed batch so running hours stay even.  A fault on the duty pump "
             "transfers to the standby automatically and records which pump failed first.")
save("ladder_pumps", W, H)
