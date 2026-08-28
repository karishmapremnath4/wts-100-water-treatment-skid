#!/usr/bin/env python3
"""WTS-100 historian.

Two jobs, both of which a real SCADA does:

  1  LOG      append every scan to a CSV, so a batch can be reviewed after
               the fact.  This is the evidence a FAT is signed off against.
  2  STATUS   write the current values to status.json, which the HMI polls.

Kept deliberately simple.  A production system would use a time series
database, but the pattern is the same: sample on a fixed period, timestamp
every row, and never lose the alarm transitions between samples.
"""
import csv, json, os, time
from pathlib import Path

FIELDS = [
    "iso_time", "elapsed_s", "state",
    "LT_101_mm", "LT_102_mm", "TT_102_C", "FT_101_m3h", "FT_103_lh", "PT_101_bar",
    "FCV_101_pct", "HTR_101_pct", "P_103_pct", "P_102_pct",
    "flow_sp_m3h", "dose_sp_lh", "level_sp_mm", "temp_sp_C",
    "MTR_101A", "MTR_101B", "XV_101", "XV_102", "HTR_EN",
    "perm_pumps", "perm_heater", "perm_inlet",
    "trip", "first_out", "alarm_first", "active_alarms",
]


class Historian:
    def __init__(self, folder=".", period_s=1.0):
        self.dir = Path(folder)
        self.dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.csv_path = self.dir / f"batch_{stamp}.csv"
        self.status_path = self.dir / "status.json"
        self.period = period_s
        self._last = 0.0
        self._f = open(self.csv_path, "w", newline="")
        self._w = csv.DictWriter(self._f, fieldnames=FIELDS)
        self._w.writeheader()
        self.rows = 0
        self._prev_state = None
        self._prev_alarms = set()
        self.events = []          # state changes and alarm transitions

    def sample(self, elapsed, ai, out, ctl):
        now = time.time()
        active = {k for k, v in ctl.alarms.items() if v}

        # events are recorded the moment they happen, not on the sample tick,
        # so a short lived alarm between samples is never lost
        if out["state"] != self._prev_state:
            self.events.append((round(elapsed, 1), "STATE", f"{self._prev_state} -> {out['state']}"))
            self._prev_state = out["state"]
        for a in sorted(active - self._prev_alarms):
            self.events.append((round(elapsed, 1), "ALARM ON", f"A-{a:03d}"))
        for a in sorted(self._prev_alarms - active):
            self.events.append((round(elapsed, 1), "ALARM OFF", f"A-{a:03d}"))
        self._prev_alarms = active

        if now - self._last < self.period:
            return
        self._last = now

        row = dict(
            iso_time=time.strftime("%Y-%m-%dT%H:%M:%S"),
            elapsed_s=round(elapsed, 1),
            state=out["state"],
            LT_101_mm=round(ai["LT_101"][0], 1),
            LT_102_mm=round(ai["LT_102"][0], 1),
            TT_102_C=round(ai["TT_102"][0], 2),
            FT_101_m3h=round(ai["FT_101"][0], 2),
            FT_103_lh=round(ai["FT_103"][0], 1),
            PT_101_bar=round(ai["PT_101"][0], 2),
            FCV_101_pct=round(out["ao"]["FCV_101"], 1),
            HTR_101_pct=round(out["ao"]["HTR_101"], 1),
            P_103_pct=round(out["ao"]["P_103"], 1),
            P_102_pct=round(out["ao"]["P_102"], 1),
            flow_sp_m3h=round(out["flow_sp"], 2),
            dose_sp_lh=round(out["dose_sp"], 1),
            level_sp_mm=ctl.level_sp,
            temp_sp_C=ctl.temp_sp,
            MTR_101A=int(out["coils"]["MTR_101A"]),
            MTR_101B=int(out["coils"]["MTR_101B"]),
            XV_101=int(out["coils"]["XV_101"]),
            XV_102=int(out["coils"]["XV_102"]),
            HTR_EN=int(out["coils"]["HTR_EN"]),
            perm_pumps=int(out["perm"]["pumps"]),
            perm_heater=int(out["perm"]["heater"]),
            perm_inlet=int(out["perm"]["inlet"]),
            trip=int(out["trip"]),
            first_out=out["first_out"],
            alarm_first=out["alarm_first"],
            active_alarms=" ".join(f"A-{a:03d}" for a in sorted(active)),
        )
        self._w.writerow(row)
        self._f.flush()
        self.rows += 1

        status = dict(row)
        status["events"] = self.events[-25:]
        status["alarm_names"] = [ALARM_TEXT[a] for a in sorted(active)]
        tmp = self.status_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(status))
        os.replace(tmp, self.status_path)      # atomic, so the HMI never reads a half written file

    def close(self):
        self._f.close()


ALARM_TEXT = {
    1: "A-001 Emergency stop",
    2: "A-002 Over temperature",
    3: "A-003 Both raw pumps failed",
    4: "A-004 Treatment tank too full",
    5: "A-005 Raw tank empty",
    6: "A-006 Duty pump failed",
    7: "A-007 Analog signal bad",
    8: "A-008 Signal not changing",
    9: "A-009 Sequence timeout",
    10: "A-010 Temperature deviation",
    11: "A-011 Pump feedback mismatch",
    12: "A-012 Dosing deviation",
}
