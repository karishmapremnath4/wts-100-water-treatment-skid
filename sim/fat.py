#!/usr/bin/env python3
"""WTS-100 Factory Acceptance Test.

Run:  python3 fat.py

Drives the real controller against the real plant model and deliberately breaks
things, one at a time, to prove each interlock does what the control narrative
says it does.

A FAT does not test the happy path.  Anyone can show a plant working when
everything is fine.  The test is whether it fails safely, so every case here
starts from a healthy running plant and then breaks exactly one thing.

Results are written to fat_results.md, which is the record you sign off.
"""
import sys, time, io
from plant import Plant
from plc import Controller
import modbus_map as M

DT = 0.5          # simulated seconds per scan


def readings(p):
    """Plant sensors, converted the same way the real controller sees them."""
    r = p.readings()
    counts = M.encode_ai(r)
    ai = M.decode_ai(counts)
    di = {k: r[k] for k in M.DI}
    return ai, di, r


def apply(p, out):
    c, a = out["coils"], out["ao"]
    p.cmd_pump_a, p.cmd_pump_b = c["MTR_101A"], c["MTR_101B"]
    p.cmd_xv101, p.cmd_xv102, p.cmd_htr_en = c["XV_101"], c["XV_102"], c["HTR_EN"]
    p.cmd_fcv_pct, p.cmd_htr_pct = a["FCV_101"], a["HTR_101"]
    p.cmd_dose_pct, p.cmd_p102_pct = a["P_103"], a["P_102"]


class Rig:
    """A plant and a controller wired together, with no Modbus in the way."""

    def __init__(s):
        s.p, s.c = Plant(dt=DT), Controller()
        s.out = None

    def run(s, seconds, start=False, reset=False, abort=False):
        for _ in range(int(seconds / DT)):
            ai, di, _ = readings(s.p)
            s.out = s.c.scan(ai, di, DT, start=start, reset=reset, abort=abort)
            apply(s.p, s.out)
            s.p.step()
            start = reset = abort = False       # momentary pushbuttons
        return s.out

    def to_running(s, level_mm=1500):
        """Bring the plant to a normal running condition before a test."""
        s.run(2, start=True)
        for _ in range(20000):
            if s.p.t102.level_mm >= level_mm:
                break
            s.run(DT)
        return s.out


RESULTS = []


def case(num, ref, title, expected, fn):
    buf = io.StringIO()
    try:
        actual, ok = fn()
    except Exception as e:
        actual, ok = f"exception: {e}", False
    RESULTS.append(dict(num=num, ref=ref, title=title,
                        expected=expected, actual=actual, passed=ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {num}  {title}")
    if not ok:
        print(f"        expected: {expected}")
        print(f"        actual:   {actual}")


# ---------------------------------------------------------------- test cases

def t01():
    r = Rig(); r.to_running()
    r.p.estop_pressed = True
    o = r.run(2)
    ok = (o["trip"] and not any(o["perm"].values()) and o["first_out"] == 1
          and not o["coils"]["MTR_101A"] and not o["coils"]["HTR_EN"])
    return (f"trip={o['trip']} perms={list(o['perm'].values())} "
            f"first_out={o['first_out']}"), ok

def t02():
    r = Rig(); r.to_running()
    r.p.estop_pressed = True; r.run(2)
    r.p.estop_pressed = False; o = r.run(5)
    return f"trip still {o['trip']} after cause cleared", o["trip"] is True

def t03():
    r = Rig(); r.to_running()
    r.p.estop_pressed = True; r.run(2)
    o = r.run(2, reset=True)
    held = o["trip"]
    r.p.estop_pressed = False; r.run(2)
    o2 = r.run(2, reset=True)
    ok = held and not o2["trip"]
    return f"reset with cause present trip={held}, after clearing trip={o2['trip']}", ok

def t04():
    r = Rig(); r.to_running()
    r.p.t101.level_mm = 100.0            # below the low low switch
    o = r.run(3)
    return (f"perm_pumps={o['perm']['pumps']} MTR_101A={o['coils']['MTR_101A']}",
            not o["perm"]["pumps"] and not o["coils"]["MTR_101A"])

def t05():
    r = Rig(); r.to_running()
    r.p.t102.level_mm = 2400.0           # above the high high switch
    o = r.run(3)
    return (f"perm_pumps={o['perm']['pumps']} perm_inlet={o['perm']['inlet']} "
            f"XV_101={o['coils']['XV_101']}",
            not o["perm"]["pumps"] and not o["perm"]["inlet"]
            and not o["coils"]["XV_101"])

def t06():
    r = Rig(); r.to_running()
    r.p.t102.level_mm = 500.0            # below the 800 mm heater permissive
    o = r.run(3)
    return (f"perm_heater={o['perm']['heater']} HTR_EN={o['coils']['HTR_EN']} "
            f"perm_pumps={o['perm']['pumps']}",
            not o["perm"]["heater"] and not o["coils"]["HTR_EN"]
            and o["perm"]["pumps"])      # pumps must KEEP running to refill

def t07():
    r = Rig(); r.to_running()
    r.p.fault_lt102_break = True         # cut the transmitter wire
    o = r.run(3)
    return (f"perm_heater={o['perm']['heater']} HTR_EN={o['coils']['HTR_EN']}",
            not o["perm"]["heater"] and not o["coils"]["HTR_EN"])

def t08():
    r = Rig(); r.to_running()
    r.p.fault_pump_a = True              # duty pump overload
    o = r.run(8)
    return (f"trip={o['trip']} MTR_101A={o['coils']['MTR_101A']} "
            f"MTR_101B={o['coils']['MTR_101B']}",
            not o["trip"] and o["coils"]["MTR_101B"] and not o["coils"]["MTR_101A"])

def t09():
    r = Rig(); r.to_running()
    r.p.fault_pump_a = True; r.run(8)
    r.p.fault_pump_b = True; o = r.run(10)
    return (f"trip={o['trip']} first_out={o['first_out']} "
            f"perms={list(o['perm'].values())}",
            o["trip"] and o["first_out"] == 6 and not any(o["perm"].values()))

def t10():
    r = Rig(); r.to_running(level_mm=1250)
    o = r.out
    return f"state={o['state']} at {r.p.t102.level_mm:.0f} mm", o["state"] == "HEAT"

def t11():
    r = Rig(); r.to_running()
    r.p.temp_c = 90.0                    # above the fixed 85 degC thermostat
    o = r.run(3)
    return (f"perm_heater={o['perm']['heater']} trip={o['trip']} "
            f"first_out={o['first_out']}",
            not o["perm"]["heater"] and o["trip"] and o["first_out"] == 4)

def t12():
    r = Rig(); r.to_running()
    o = r.run(2, abort=True)
    return (f"state={o['state']} HTR_EN={o['coils']['HTR_EN']} "
            f"MTR_101A={o['coils']['MTR_101A']} XV_101={o['coils']['XV_101']}",
            o["state"] == "IDLE" and not o["coils"]["HTR_EN"]
            and not o["coils"]["MTR_101A"] and not o["coils"]["XV_101"])


def t13():
    r = Rig(); r.to_running(level_mm=1900)
    for _ in range(4000):                       # get into DISCHARGE
        r.run(DT)
        if r.out["state"] == "DISCHARGE":
            break
    r.p.fault_discharge_blocked = True          # blocked outlet
    o = r.run(30)
    return (f"state={o['state']} P_102={o['ao']['P_102']:.0f}% "
            f"XV_102={o['coils']['XV_102']}",
            o["ao"]["P_102"] == 0.0)


def t14():
    r = Rig(); r.to_running()
    r.p.fault_lt102_stuck = True                # transmitter freezes, reading stays valid
    o = r.run(320)
    return (f"A-008={r.c.alarms.get(8)} trip={o['trip']} "
            f"perm_heater={o['perm']['heater']}",
            r.c.alarms.get(8) is True and not o["trip"])


CASES = [
 ("FAT-01","I1","Emergency stop removes every permission and trips",
  "all three permissions FALSE, trip latched, first out I1, heater and pumps off",t01),
 ("FAT-02","I1","Trip stays latched after the cause clears",
  "trip remains TRUE when the e-stop is released",t02),
 ("FAT-03","I1","Reset only works once the cause has gone",
  "reset with cause present has no effect, reset after clearing works",t03),
 ("FAT-04","I2","Raw tank low low stops the pumps",
  "perm_pumps FALSE, pump contactor off",t04),
 ("FAT-05","I3","Treatment tank high high stops all inflow",
  "perm_pumps and perm_inlet FALSE, XV-101 closed",t05),
 ("FAT-06","I5","Low level blocks the heater but NOT the pumps",
  "perm_heater FALSE, heater off, perm_pumps still TRUE so the tank can refill",t06),
 ("FAT-07","I7","Broken level transmitter blocks the heater",
  "perm_heater FALSE, heater off",t07),
 ("FAT-08","5","One pump fault changes over to the standby without tripping",
  "no trip, P-101B running, P-101A stopped",t08),
 ("FAT-09","I6","Both pumps faulted trips the plant",
  "trip latched, first out I6, all permissions FALSE",t09),
 ("FAT-10","4.1","Sequence advances FILL to HEAT at 1200 mm",
  "state is HEAT once the level passes 1200 mm",t10),
 ("FAT-11","I4","Over temperature blocks the heater and trips",
  "perm_heater FALSE, trip latched, first out I4",t11),
 ("FAT-12","4.8","Controlled stop shuts down in the correct order",
  "state IDLE, heater off, pumps off, valves closed",t12),
 ("FAT-13","I8","Blocked discharge stops the discharge pump",
  "P-102 driven to 0 percent when the level stops falling for 20 s",t13),
 ("FAT-14","A-008","Frozen transmitter raises an alarm but does NOT trip",
  "A-008 active, no trip, because a steady process can also read steady",t14),
]


if __name__ == "__main__":
    print("WTS-100 FACTORY ACCEPTANCE TEST")
    print("=" * 66)
    t0 = time.time()
    for num, ref, title, exp, fn in CASES:
        case(num, ref, title, exp, fn)
    dur = time.time() - t0

    npass = sum(1 for r in RESULTS if r["passed"])
    print("=" * 66)
    print(f"{npass} of {len(RESULTS)} passed in {dur:.1f} s")

    with open("fat_results.md", "w") as f:
        f.write("# WTS-100 Factory Acceptance Test, results\n\n")
        f.write(f"Run {time.strftime('%Y-%m-%d %H:%M')}   |   "
                f"**{npass} of {len(RESULTS)} passed**\n\n")
        f.write("Each case starts from a healthy running plant and breaks exactly "
                "one thing. Reference is the interlock or narrative section under test.\n\n")
        f.write("| # | Ref | Test | Expected | Actual | Result |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in RESULTS:
            f.write(f"| {r['num']} | {r['ref']} | {r['title']} | {r['expected']} "
                    f"| `{r['actual']}` | {'PASS' if r['passed'] else 'FAIL'} |\n")
        f.write("\n\n## Witness\n\n")
        f.write("| | |\n|---|---|\n| Tested by | K. Premnath |\n"
                "| Witnessed by | (open) |\n| Date | "
                + time.strftime("%Y-%m-%d") + " |\n")
    print("results written to fat_results.md")
    sys.exit(0 if npass == len(RESULTS) else 1)
