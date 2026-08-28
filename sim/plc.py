#!/usr/bin/env python3
"""WTS-100 controller.

Run the plant first:   python3 plant_server.py
Then this:             python3 plc.py

Connects to the plant over Modbus TCP and executes the control program every
scan, in the order a PLC does:

    1  READ    every input, frozen for the scan
    2  SOLVE   safety, then pumps, then loops, then sequence, then alarms
    3  WRITE   every output at once

Safety runs FIRST, so nothing downstream can command an output it has
inhibited.  This mirrors POU_SAFETY, POU_PUMPS, POU_SEQUENCE and POU_ALARMS.
"""
import time, argparse, sys
from pymodbus.client import ModbusTcpClient
import modbus_map as M
from historian import Historian

HOST, PORT, SCAN = "127.0.0.1", 5020, 0.1


# ---------------------------------------------------------------- PID block
class PID:
    """PID with anti-windup and a deadband.

    Anti-windup matters: with the valve already at 100 percent and the level
    still low, the integral term would keep accumulating even though the
    output cannot rise.  When the level recovered it would take a long time to
    unwind and overshoot badly.  So integration is frozen while the output is
    clamped.
    """
    def __init__(s, kp, ti, td=0.0, lo=0.0, hi=100.0, deadband=0.0, reverse=True):
        s.kp, s.ti, s.td = kp, ti, td
        s.lo, s.hi, s.db = lo, hi, deadband
        s.reverse = reverse
        s.i = 0.0
        s.prev_e = 0.0
        s.out = 0.0

    def step(s, sp, pv, dt, enable=True):
        if not enable:
            s.i = 0.0
            s.out = s.lo
            return s.out
        e = (sp - pv) if s.reverse else (pv - sp)
        if abs(e) < s.db:
            e = 0.0
        p = s.kp * e
        d = s.kp * s.td * (e - s.prev_e) / dt if s.td > 0 else 0.0
        s.prev_e = e

        cand = p + s.i + d
        if s.lo < cand < s.hi and s.ti > 0:          # only integrate when free
            s.i += s.kp * e * dt / s.ti
        s.out = max(s.lo, min(s.hi, p + s.i + d))
        return s.out


# ---------------------------------------------------------------- controller
class Controller:
    S = ["IDLE", "FILL", "HEAT", "HOLD", "DISCHARGE", "DRAIN", "TRIP", "PAUSE"]

    def __init__(s, temp_sp=45.0, level_sp=1800.0, ratio=8.0, residence_s=600.0):
        s.temp_sp, s.level_sp, s.ratio, s.residence_s = temp_sp, level_sp, ratio, residence_s
        # loops, tuned per the narrative
        s.lic102 = PID(1.2, 240, 0,  0, 50,  deadband=10.0)   # level  -> flow SP
        s.fic101 = PID(0.8,  12, 0,  0, 100, deadband=0.2)    # flow   -> valve
        s.tic102 = PID(4.0, 180, 20, 0, 100, deadband=0.5)    # temp   -> heater
        s.ffic103 = PID(0.6,  8, 0,  0, 100, deadband=2.0)    # dosing -> pump

        s.state = 0
        s.trip = False
        s.first_out = 0
        s.duty_is_a = True
        s.fault_a = s.fault_b = False
        s.tA = s.tB = 0.0
        s.t_state = 0.0
        s.t_stable = 0.0
        s.t_residence = 0.0
        s.t_drain = 0.0
        s.t_ain = 0.0
        s.alarms = {}
        s.alarm_first = 0
        s.alm_on_delay = {}   # ISA-18.2: stop process alarms chattering on noise
        s.t_deadhead = 0.0
        s.lvl_prev = None
        s.deadhead = False
        s.stuck_prev = {}
        s.stuck_t = {}

    # ------------------------------------------------------------ one scan
    def scan(s, ai, di, dt, start=False, reset=False, abort=False):
        lt102, lt102_ok = ai["LT_102"]
        tt102, tt102_ok = ai["TT_102"]
        lt101, _        = ai["LT_101"]
        ft101, _        = ai["FT_101"]
        ft103, _        = ai["FT_103"]

        # ---- I7: sustained analog fault ---------------------------------
        s.t_ain = s.t_ain + dt if not (lt102_ok and tt102_ok) else 0.0
        ain_fault = s.t_ain >= 30.0

        # ---- POU_SAFETY --------------------------------------------------
        trip_cause = ((not di["ESD_01_OK"]) or (not di["TSHH_102_OK"])
                      or ((not di["XA_101A_OK"]) and (not di["XA_101B_OK"]))
                      or ain_fault)
        if trip_cause:
            s.trip = True
            if s.first_out == 0:
                s.first_out = (1 if not di["ESD_01_OK"] else
                               4 if not di["TSHH_102_OK"] else
                               6 if not (di["XA_101A_OK"] or di["XA_101B_OK"]) else 7)
        elif reset:
            s.trip, s.first_out = False, 0

        perm_pumps  = di["ESD_01_OK"] and di["LSLL_101_OK"] and di["LSHH_102_OK"] and not s.trip
        perm_heater = (di["ESD_01_OK"] and di["TSHH_102_OK"] and lt102_ok and tt102_ok
                       and lt102 >= 800.0 and not s.trip)
        perm_inlet  = di["ESD_01_OK"] and di["LSHH_102_OK"] and not s.trip

        # ---- POU_SEQUENCE ------------------------------------------------
        prev = s.state
        if s.trip:
            s.state = 6
        elif abort:
            s.state = 0

        st = s.state
        run_pumps = xv101 = xv102 = htr_en = dosing = cascade = False
        flow_sp = p102 = 0.0

        if st == 0:                                            # IDLE
            if start and not s.trip and lt101 > 400.0:
                s.state = 1
        elif st == 1:                                          # FILL
            xv101, run_pumps, flow_sp = perm_inlet, True, 30.0
            if lt102 >= 1200.0: s.state = 2
        elif st == 2:                                          # HEAT
            xv101, run_pumps, cascade = perm_inlet, True, True
            htr_en, dosing = perm_heater, True
            s.t_stable = s.t_stable + dt if abs(tt102 - s.temp_sp) <= 0.5 else 0.0
            if s.t_stable >= 60.0: s.state = 3
        elif st == 3:                                          # HOLD
            cascade, htr_en, dosing = True, perm_heater, True
            s.t_residence += dt
            if s.t_residence >= s.residence_s: s.state = 4
        elif st == 4:                                          # DISCHARGE
            xv102, p102 = True, 60.0
            if lt102 <= 300.0: s.state = 5
        elif st == 5:                                          # DRAIN
            xv102, p102 = True, 100.0
            s.t_drain = s.t_drain + dt if lt102 <= 50.0 else 0.0
            if s.t_drain >= 10.0:
                xv102, p102, s.state = False, 0.0, 0
        elif st == 6:                                          # TRIP
            if not s.trip: s.state = 0

        if s.state != prev:                                    # state changed
            s.t_state = 0.0
            if prev == 5 and s.state == 0:                     # batch complete
                s.duty_is_a = not s.duty_is_a                  # alternate duty
                s.t_residence = 0.0
            s.t_stable = s.t_drain = 0.0
        else:
            s.t_state += dt

        timeout = {1: 900.0, 2: 5400.0, 4: 600.0}.get(s.state, 0.0)
        seq_timeout = timeout > 0 and s.t_state > timeout
        if seq_timeout:
            s.state = 5

        # ---- loops --------------------------------------------------------
        if cascade:
            flow_sp = s.lic102.step(s.level_sp, lt102, dt)
        fcv = s.fic101.step(flow_sp, ft101, dt, enable=(run_pumps and perm_inlet))
        htr = s.tic102.step(s.temp_sp, tt102, dt, enable=(htr_en and perm_heater))
        dose_sp = ft101 * s.ratio if (dosing and ft101 >= 2.0) else 0.0
        dose = s.ffic103.step(dose_sp, ft103, dt, enable=(dose_sp > 0))

        # ---- POU_PUMPS ----------------------------------------------------
        run_req = run_pumps and perm_pumps
        mtr_a = run_req and s.duty_is_a and not s.fault_a
        mtr_b = run_req and not s.fault_b and ((not s.duty_is_a) or s.fault_a)
        # NOTE: dt here is PROCESS time.  The scan must advance less process
        # time than the shortest timer, or the timer expires before feedback
        # can ever arrive.  At speed 60 a scan is 6 s and this 3 s timer
        # faulted both pumps on the first scan.  Keep speed at 10 or below.
        s.tA = s.tA + dt if (mtr_a and not di["XS_101A"]) else 0.0
        s.tB = s.tB + dt if (mtr_b and not di["XS_101B"]) else 0.0
        if s.tA >= 3.0: s.fault_a = True
        if s.tB >= 3.0: s.fault_b = True

        # ---- I8: discharge pump deadhead ---------------------------------
        # The narrative specified this against FT-101, the INLET flowmeter,
        # which is a different pipe and could never have detected a blocked
        # discharge.  There is no discharge flowmeter in the instrument index,
        # so it is detected instead by the tank level failing to fall while
        # the discharge pump is running.  That uses LT-102, which exists.
        if s.state in (4, 5) and p102 > 0 and lt102_ok:
            if s.lvl_prev is not None and (s.lvl_prev - lt102) < 0.5 * dt:
                s.t_deadhead += dt
            else:
                s.t_deadhead = 0.0
            if s.t_deadhead >= 20.0:
                s.deadhead = True
        else:
            s.t_deadhead = 0.0
        s.lvl_prev = lt102 if lt102_ok else s.lvl_prev
        if s.deadhead:
            p102 = 0.0
            xv102 = False

        # ---- A-008: frozen sensor ----------------------------------------
        # The dangerous failure.  A transmitter that keeps reporting its last
        # good value stays inside the valid range and looks perfectly healthy,
        # so range checks never catch it.  Detected by the reading not moving
        # at all while the process should be changing.
        moving = run_pumps or htr_en or p102 > 0
        stuck_any = False
        for tag, val in (("LT_102", lt102), ("TT_102", tt102), ("FT_101", ft101)):
            prev = s.stuck_prev.get(tag)
            if moving and prev is not None and abs(val - prev) < 1e-9:
                s.stuck_t[tag] = s.stuck_t.get(tag, 0.0) + dt
            else:
                s.stuck_t[tag] = 0.0
            s.stuck_prev[tag] = val
            if s.stuck_t.get(tag, 0.0) >= 300.0:
                stuck_any = True

        # ---- POU_ALARMS ---------------------------------------------------
        # Safety alarms act immediately.  Process deviation alarms do not,
        # for two reasons found by watching the HMI:
        #
        #   A-010 was alarming through the whole heat up.  Deviation from
        #   setpoint is NORMAL while heating, so it is only meaningful once
        #   the sequence says we should already be at temperature, ie HOLD.
        #
        #   A-012 was chattering, on and off four times in four seconds,
        #   because measurement noise crossed the threshold repeatedly.  A
        #   chattering alarm is worse than no alarm: operators learn to
        #   ignore the whole system.  Both deviation alarms now need the
        #   condition to persist before they are raised.
        raw = {
            1: not di["ESD_01_OK"], 2: not di["TSHH_102_OK"],
            3: s.fault_a and s.fault_b, 4: not di["LSHH_102_OK"],
            5: not di["LSLL_101_OK"], 6: s.fault_a or s.fault_b,
            7: not (lt102_ok and tt102_ok), 8: stuck_any,
            9: seq_timeout,
            10: abs(tt102 - s.temp_sp) > 5.0 and s.state == 3,      # HOLD only
            11: s.deadhead,
            12: dose_sp > 0 and abs(ft103 - dose_sp) > 0.2 * dose_sp,
        }
        ON_DELAY = {10: 10.0, 12: 10.0}          # seconds the condition must persist
        s.alarms = {}
        for k, v in raw.items():
            d = ON_DELAY.get(k)
            if d is None:
                s.alarms[k] = v                  # safety alarms, no delay
            else:
                s.alm_on_delay[k] = s.alm_on_delay.get(k, 0.0) + dt if v else 0.0
                s.alarms[k] = s.alm_on_delay[k] >= d
        any_alarm = any(s.alarms.values())
        if any_alarm and s.alarm_first == 0:
            s.alarm_first = next(k for k, v in s.alarms.items() if v)
        if not any_alarm:
            s.alarm_first = 0

        return dict(
            coils={"MTR_101A": mtr_a, "MTR_101B": mtr_b,
                   "XV_101": xv101 and perm_inlet, "XV_102": xv102,
                   "HTR_EN": htr_en and perm_heater, "MTR_102": p102 > 0,
                   "ALM_H": any_alarm, "ALM_B": any_alarm},
            ao={"FCV_101": fcv, "HTR_101": htr, "P_103": dose, "P_102": p102},
            perm=dict(pumps=perm_pumps, heater=perm_heater, inlet=perm_inlet),
            state=s.S[s.state], trip=s.trip, first_out=s.first_out,
            alarm_first=s.alarm_first, flow_sp=flow_sp, dose_sp=dose_sp,
        )


# ---------------------------------------------------------------------- main
def main(seconds, quiet=False, speed=10.0, log=True):
    c = ModbusTcpClient(HOST, port=PORT)
    if not c.connect():
        print(f"cannot reach the plant on {HOST}:{PORT}.  Start plant_server.py first.")
        sys.exit(1)

    ctl = Controller()
    hist = Historian(folder=".", period_s=1.0) if log else None
    t0, last, started = time.time(), time.time(), False
    print(f"{'time':>6} {'state':>10} {'lvl mm':>8} {'temp C':>7} {'flow':>6} "
          f"{'valve':>6} {'htr':>5} {'pumpA':>6} {'trip':>5}")

    while time.time() - t0 < seconds:
        now = time.time()
        dt = now - last
        if dt < SCAN:
            time.sleep(SCAN - dt); now = time.time(); dt = now - last
        last = now

        ir = c.read_input_registers(address=0, count=len(M.AI))
        dib = c.read_discrete_inputs(address=0, count=len(M.DI))
        if ir.isError() or dib.isError():
            print("modbus read error"); break

        ai = M.decode_ai(ir.registers)
        di = {n: bool(dib.bits[i]) for n, i in M.DI.items()}

        start = not started
        out = ctl.scan(ai, di, dt * speed, start=start)   # dt in PROCESS time
        if start: started = True

        coil_vals = [0]*len(M.DO)
        for n, i in M.DO.items(): coil_vals[i] = int(out["coils"][n])
        c.write_coils(address=0, values=coil_vals)

        hr = [0]*len(M.AO)
        for n, (i, lo, hi) in M.AO.items():
            hr[i] = M.eu_to_counts(out["ao"][n], lo, hi)
        c.write_registers(address=0, values=hr)

        if hist:
            hist.sample((now - t0) * speed, ai, out, ctl)

        if not quiet:
            print(f"{now-t0:6.1f} {out['state']:>10} {ai['LT_102'][0]:8.0f} "
                  f"{ai['TT_102'][0]:7.1f} {ai['FT_101'][0]:6.1f} "
                  f"{out['ao']['FCV_101']:6.1f} {out['ao']['HTR_101']:5.1f} "
                  f"{str(out['coils']['MTR_101A']):>6} {str(out['trip']):>5}")
    c.close()
    if hist:
        hist.close()
        print(f"\nlogged {hist.rows} rows to {hist.csv_path.name}")
        print(f"{len(hist.events)} events recorded")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-log", dest="log", action="store_false",
                    help="do not write the CSV or status.json")
    ap.add_argument("--speed", type=float, default=10.0,
                    help="must match plant_server.py --speed")
    main(**vars(ap.parse_args()))
