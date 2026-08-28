"""Execute the ladder rungs exactly as drawn and test the safety behaviour."""

class PLC:
    def __init__(s):
        s.TRIP = False; s.RUN_REQ = False
        s.FAULT_A = False; s.FAULT_B = False
        s.tA = 0; s.tB = 0; s.DUTY_IS_A = True

    def scan(s, i, dt=1.0):
        # ---------------- POU_SAFETY ----------------
        # R1: causes in PARALLEL (any one trips). The two overloads are in series.
        s.TRIP_CAUSE = ((not i['ESD_01_OK']) or (not i['TSHH_102_OK'])
                        or ((not i['XA_101A_OK']) and (not i['XA_101B_OK']))
                        or i['AIN_FAULT'])
        # R2 latch / R3 unlatch
        if s.TRIP_CAUSE:                                s.TRIP = True
        elif i['HS_04_RESET'] and not s.TRIP_CAUSE:     s.TRIP = False

        # R4..R6 permissives
        s.PERM_RAW_PUMPS = (i['ESD_01_OK'] and i['LSLL_101_OK']
                            and i['LSHH_102_OK'] and not s.TRIP)
        s.PERM_HEATER    = (i['ESD_01_OK'] and i['TSHH_102_OK'] and i['LT_102_VALID']
                            and i['TT_102_VALID'] and i['LVL_ABOVE_800'] and not s.TRIP)
        s.PERM_INLET     = (i['ESD_01_OK'] and i['LSHH_102_OK'] and not s.TRIP)

        # ---------------- POU_PUMPS ----------------
        # R1: seal-in parallels START ONLY; STOP and PERM are in series AFTER the block
        s.RUN_REQ = ((i['HS_02_START'] or s.RUN_REQ)
                     and i['HS_03_STOP_OK'] and s.PERM_RAW_PUMPS)
        # R2, R3
        s.MTR_101A = s.RUN_REQ and s.DUTY_IS_A and not s.FAULT_A
        s.MTR_101B = ((s.RUN_REQ and (not s.DUTY_IS_A) and not s.FAULT_B)
                      or (s.RUN_REQ and s.FAULT_A and not s.FAULT_B))
        # R4, R5: 3 s on-delay then latch
        s.tA = s.tA + dt if (s.MTR_101A and not i['XS_101A']) else 0
        s.tB = s.tB + dt if (s.MTR_101B and not i['XS_101B']) else 0
        if s.tA >= 3: s.FAULT_A = True
        if s.tB >= 3: s.FAULT_B = True
        # R6
        s.BOTH_PUMPS_FAILED = s.FAULT_A and s.FAULT_B
        return s

HEALTHY = dict(ESD_01_OK=True, TSHH_102_OK=True, XA_101A_OK=True, XA_101B_OK=True,
               AIN_FAULT=False, LSLL_101_OK=True, LSHH_102_OK=True,
               LT_102_VALID=True, TT_102_VALID=True, LVL_ABOVE_800=True,
               HS_04_RESET=False, HS_02_START=False, HS_03_STOP_OK=True,
               XS_101A=True, XS_101B=True)

def run(overrides=None, scans=1, p=None):
    p = p or PLC(); i = dict(HEALTHY); i.update(overrides or {})
    for _ in range(scans): p.scan(i)
    return p

fails = []
def check(name, got, want):
    ok = got == want
    if not ok: fails.append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")

print("POU_SAFETY")
check("healthy: no trip",                      run().TRIP, False)
check("e-stop pressed trips",                  run({'ESD_01_OK':False}).TRIP, True)
check("over-temperature trips",                run({'TSHH_102_OK':False}).TRIP, True)
check("ONE pump overload does NOT trip",       run({'XA_101A_OK':False}).TRIP, False)
check("BOTH pump overloads trip",              run({'XA_101A_OK':False,'XA_101B_OK':False}).TRIP, True)
check("analog invalid trips",                  run({'AIN_FAULT':True}).TRIP, True)
check("e-stop kills raw pump permission",      run({'ESD_01_OK':False}).PERM_RAW_PUMPS, False)
check("e-stop kills heater permission",        run({'ESD_01_OK':False}).PERM_HEATER, False)
check("e-stop kills inlet permission",         run({'ESD_01_OK':False}).PERM_INLET, False)
check("low level blocks heater",               run({'LVL_ABOVE_800':False}).PERM_HEATER, False)
check("invalid level blocks heater",           run({'LT_102_VALID':False}).PERM_HEATER, False)
check("invalid temp blocks heater",            run({'TT_102_VALID':False}).PERM_HEATER, False)
check("tank full blocks raw pumps",            run({'LSHH_102_OK':False}).PERM_RAW_PUMPS, False)
check("tank empty blocks raw pumps",           run({'LSLL_101_OK':False}).PERM_RAW_PUMPS, False)

p = run({'ESD_01_OK':False})                     # trip it
p.scan(dict(HEALTHY, ESD_01_OK=False, HS_04_RESET=True))
check("reset while cause present stays tripped", p.TRIP, True)
p.scan(dict(HEALTHY, HS_04_RESET=True))
check("reset after cause clears works",          p.TRIP, False)

print("\nPOU_PUMPS")
p = PLC(); p.scan(dict(HEALTHY, HS_02_START=True))
check("start energises RUN_REQ",               p.RUN_REQ, True)
p.scan(dict(HEALTHY))
check("seal in holds after button released",   p.RUN_REQ, True)
p.scan(dict(HEALTHY, HS_03_STOP_OK=False))
check("STOP breaks the seal in",               p.RUN_REQ, False)

p = PLC(); p.scan(dict(HEALTHY, HS_02_START=True)); p.scan(dict(HEALTHY))
p.scan(dict(HEALTHY, ESD_01_OK=False))
check("e-stop breaks the seal in",             p.RUN_REQ, False)

p = PLC(); p.scan(dict(HEALTHY, HS_02_START=True))
check("duty A runs, B does not",               (p.MTR_101A, p.MTR_101B), (True, False))

p = PLC()
for _ in range(5): p.scan(dict(HEALTHY, HS_02_START=True, XS_101A=False))
check("A with no feedback faults after 3 s",   p.FAULT_A, True)
check("standby B started automatically",       p.MTR_101B, True)
check("A stopped",                             p.MTR_101A, False)
check("not both-failed yet",                   p.BOTH_PUMPS_FAILED, False)
for _ in range(5): p.scan(dict(HEALTHY, HS_02_START=True, XS_101A=False, XS_101B=False))
check("both failed raises I6",                 p.BOTH_PUMPS_FAILED, True)

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
