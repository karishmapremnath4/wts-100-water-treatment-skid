#!/usr/bin/env python3
"""WTS-100 plant simulator.

First principles model of the skid: two tanks, pumps, a control valve, a heater
and a dosing pump.  The PLC talks to it over Modbus TCP exactly as it would talk
to real I/O cards, so the control code cannot tell the plant is simulated.

Physics
    Level      conservation of volume,  dV/dt = Qin - Qout
    Temperature energy balance,         m*cp*dT/dt = Qheater - Qloss
    Valve      first order lag, because a valve does not jump to position
    Sensors    gaussian noise on every measurement

Everything is in engineering units here.  Conversion to and from 4-20 mA counts
happens in modbus_map.py, which mirrors doc 04.
"""
from dataclasses import dataclass, field
import math, random


@dataclass
class Tank:
    area_m2:  float          # cross sectional area
    height_mm: float
    level_mm: float = 0.0

    def add_volume(self, m3):
        """Change level by a volume in cubic metres."""
        self.level_mm = max(0.0, min(self.height_mm,
                                     self.level_mm + (m3 / self.area_m2) * 1000.0))


@dataclass
class Actuator:
    """First order lag.  A valve or a VFD takes time to reach a new position."""
    tau_s: float
    value: float = 0.0

    def step(self, target, dt):
        a = dt / max(self.tau_s, 1e-6)
        self.value += (target - self.value) * min(a, 1.0)
        return self.value


@dataclass
class Plant:
    dt: float = 0.1

    # vessels, sized from the instrument index
    t101: Tank = field(default_factory=lambda: Tank(area_m2=3.0, height_mm=3000, level_mm=2400))
    t102: Tank = field(default_factory=lambda: Tank(area_m2=2.0, height_mm=2500, level_mm=0))
    t103_litres: float = 200.0

    # actuators
    fcv101: Actuator = field(default_factory=lambda: Actuator(tau_s=3.0))
    htr101: Actuator = field(default_factory=lambda: Actuator(tau_s=8.0))
    p103:   Actuator = field(default_factory=lambda: Actuator(tau_s=2.0))
    p102:   Actuator = field(default_factory=lambda: Actuator(tau_s=3.0))

    # process state
    temp_c: float = 18.0
    ambient_c: float = 18.0

    # commands written by the PLC
    cmd_pump_a: bool = False
    cmd_pump_b: bool = False
    cmd_xv101:  bool = False
    cmd_xv102:  bool = False
    cmd_htr_en: bool = False
    cmd_fcv_pct: float = 0.0
    cmd_htr_pct: float = 0.0
    cmd_dose_pct: float = 0.0
    cmd_p102_pct: float = 0.0

    # faults you can inject during the FAT
    fault_pump_a: bool = False
    fault_pump_b: bool = False
    fault_lt102_break: bool = False
    fault_lt102_stuck: bool = False
    estop_pressed: bool = False
    fault_discharge_blocked: bool = False
    _stuck_value: float = 0.0

    # derived
    flow_in_m3h:  float = 0.0
    flow_dose_lh: float = 0.0
    flow_out_m3h: float = 0.0

    # constants
    PUMP_HEAD_M3H: float = 45.0     # free flow of one raw water pump
    HEATER_KW:     float = 150.0    # revised: 6 kW could not meet the batch duty
    CP_KJ_KGK:     float = 4.18
    LOSS_W_PER_K:  float = 42.0     # heat loss to ambient

    def step(self):
        dt = self.dt

        # ---- actuators move toward their commanded position ----------------
        fcv  = self.fcv101.step(self.cmd_fcv_pct  if self.cmd_xv101 else 0.0, dt)
        htr  = self.htr101.step(self.cmd_htr_pct  if self.cmd_htr_en else 0.0, dt)
        dose = self.p103.step(self.cmd_dose_pct, dt)
        pout = self.p102.step(self.cmd_p102_pct  if self.cmd_xv102 else 0.0, dt)

        # ---- inlet flow -----------------------------------------------------
        pump_running = ((self.cmd_pump_a and not self.fault_pump_a) or
                        (self.cmd_pump_b and not self.fault_pump_b))
        if pump_running and self.t101.level_mm > 50 and self.cmd_xv101:
            # equal percentage valve characteristic
            frac = (fcv / 100.0) ** 1.6
            self.flow_in_m3h = self.PUMP_HEAD_M3H * frac
        else:
            self.flow_in_m3h = 0.0

        # ---- outlet flow ----------------------------------------------------
        blocked = self.fault_discharge_blocked
        self.flow_out_m3h = 0.0 if blocked else (
            (pout / 100.0) * 40.0 if self.t102.level_mm > 20 else 0.0)

        # ---- dosing ---------------------------------------------------------
        self.flow_dose_lh = (dose / 100.0) * 500.0
        self.t103_litres = max(0.0, self.t103_litres - self.flow_dose_lh * dt / 3600.0)

        # ---- level, conservation of volume ----------------------------------
        self.t101.add_volume(-self.flow_in_m3h * dt / 3600.0)
        self.t102.add_volume((self.flow_in_m3h - self.flow_out_m3h) * dt / 3600.0)

        # ---- temperature, energy balance ------------------------------------
        mass_kg = self.t102.area_m2 * (self.t102.level_mm / 1000.0) * 1000.0
        if mass_kg > 1.0:
            q_in  = self.HEATER_KW * 1000.0 * (htr / 100.0)          # watts
            q_out = self.LOSS_W_PER_K * (self.temp_c - self.ambient_c)
            # incoming cold water dilutes the heat
            q_mix = (self.flow_in_m3h / 3600.0) * 1000.0 * self.CP_KJ_KGK * 1000.0 \
                    * (self.ambient_c - self.temp_c)
            dT = (q_in - q_out + q_mix) * dt / (mass_kg * self.CP_KJ_KGK * 1000.0)
            self.temp_c = max(0.0, min(120.0, self.temp_c + dT))
        else:
            self.temp_c += (self.ambient_c - self.temp_c) * 0.01

        return self.readings()

    # ---------------------------------------------------------------- sensors
    def _noise(self, v, pct_of_span, span):
        return v + random.gauss(0.0, pct_of_span * span / 100.0)

    def readings(self):
        lt102 = self.t102.level_mm
        if self.fault_lt102_stuck:
            lt102 = self._stuck_value
        else:
            self._stuck_value = lt102

        return dict(
            LT_101 = max(0.0, self._noise(self.t101.level_mm, 0.10, 3000)),
            # a frozen transmitter outputs a CONSTANT.  No noise, or the
            # reading keeps moving and never looks stuck.
            LT_102 = (-999.0 if self.fault_lt102_break
                      else lt102 if self.fault_lt102_stuck
                      else max(0.0, self._noise(lt102, 0.10, 2500))),
            FT_101 = max(0.0, self._noise(self.flow_in_m3h, 0.15, 50)),
            FT_103 = max(0.0, self._noise(self.flow_dose_lh, 0.20, 500)),
            TT_102 = self._noise(self.temp_c, 0.05, 100),
            PT_101 = self._noise(3.2 if self.flow_in_m3h > 0 else 0.0, 0.10, 10),
            AT_102 = self._noise(420.0, 0.30, 2000),
            # discrete, all NC so TRUE means healthy
            ESD_01_OK    = not self.estop_pressed,
            LSLL_101_OK  = self.t101.level_mm > 150,
            LSHH_102_OK  = self.t102.level_mm < 2300,
            TSHH_102_OK  = self.temp_c < 85.0,
            XA_101A_OK   = not self.fault_pump_a,
            XA_101B_OK   = not self.fault_pump_b,
            XS_101A      = self.cmd_pump_a and not self.fault_pump_a,
            XS_101B      = self.cmd_pump_b and not self.fault_pump_b,
        )
