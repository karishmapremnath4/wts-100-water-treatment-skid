# Control Narrative
## WTS-100 Water Treatment and Transfer Skid

Describes how the skid behaves. The PLC program is written from this document.

---

## 1. What the skid does

Water is pumped from a raw water tank into a treatment tank. It is heated, a
chemical is added, it is held for a set time, then it is pumped out. The cycle
then repeats.

### 1.1 Equipment

| Tag | Description |
|---|---|
| T-101 | Raw water tank, 3000 mm |
| P-101A / P-101B | Raw water pumps, 3 kW. One runs, one is the spare. |
| XV-101 | Inlet isolation valve. Spring closed. |
| FCV-101 | Inlet flow control valve. Air to open. |
| T-102 | Treatment tank, 2500 mm |
| HTR-101 | Immersion heater, 6 kW |
| T-103 | Chemical tank, 200 L |
| P-103 | Dosing pump |
| XV-102 | Discharge isolation valve. Spring closed. |
| P-102 | Discharge pump |

### 1.2 Signal count

7 analog inputs, 4 analog outputs, 14 digital inputs, 8 digital outputs.
Devices are listed in WTS-100-II-001, the instrument index.

---

## 2. Modes

The operator selects the mode with switch HS-01.

**Off.** Everything is off. Both valves close.

**Hand.** The operator can run each device one at a time from the HMI. Used for
maintenance and for checking loops. All interlocks in section 5 still apply.

**Auto.** The sequence in section 4 runs. The operator can Start, Hold and Abort.

Auto can only be selected from IDLE. Selecting Hand while running stops the skid
first, in the order given in section 4.8.

---

## 3. Control loops

### 3.1 Level, LIC-102

Holds the level in T-102. It does not move the valve itself. It tells the flow
loop what flow to run.

| | |
|---|---|
| Reads | LT-102, 0 to 2500 mm |
| Setpoint | 1800 mm. Operator range 500 to 2200 mm. |
| Output | Flow setpoint to FIC-101 |
| Tuning | Kp 1.2, Ti 240 s |
| Deadband | 10 mm |

No derivative term is used.

### 3.2 Flow, FIC-101

Holds the inlet flow by moving valve FCV-101.

| | |
|---|---|
| Reads | FT-101, 0 to 50 m3/h |
| Setpoint | From LIC-102 in Auto. Set locally in Hand. |
| Output | FCV-101, 0 to 100 percent |
| Tuning | Kp 0.8, Ti 12 s |
| Cutoff | Reading forced to zero below 1.0 m3/h |

If FIC-101 is switched to local, LIC-102 follows the local setpoint. This stops
the valve jumping when cascade is switched back on.

### 3.3 Temperature, TIC-102

Holds the temperature in T-102 by adjusting heater power.

| | |
|---|---|
| Reads | TT-102, 0 to 100 degC |
| Setpoint | 45 degC. Operator range 20 to 70 degC. |
| Output | HTR-101, 0 to 100 percent |
| Tuning | Kp 4.0, Ti 180 s, Td 20 s |
| Deadband | 0.5 degC |

The output is limited to 0 to 100 percent. While it sits at a limit, the integral
term is held.

There is no cooling. The loop can only add heat.

### 3.4 Dosing, FFIC-103

Adds chemical in proportion to the water flow.

```
dose setpoint (L/h) = water flow (m3/h) x ratio (L/m3)
```

| | |
|---|---|
| Reads | FT-103, 0 to 500 L/h |
| Ratio | 8.0 L/m3. Operator range 2.0 to 20.0. |
| Output | P-103 speed, 0 to 100 percent |
| Tuning | Kp 0.6, Ti 8 s |
| Inhibit | Dosing stops when water flow is below 2.0 m3/h |

---

## 4. Sequence

One state is active at a time. Any interlock in section 5 sends the sequence to
TRIP from any state.

### 4.0 IDLE

Everything off. Both valves closed.

Go to FILL when: Start is pressed, no trip is active, and LT-101 is above 400 mm.

### 4.1 FILL

Open XV-101. Start the duty pump. Hold flow at 30 m3/h. Heater off. Dosing off.

Go to HEAT when LT-102 reaches 1200 mm.

Timeout 900 s. Raise alarm A-009 and go to DRAIN.

### 4.2 HEAT

Put LIC-102 in cascade at 1800 mm. Start the temperature loop. Start dosing.

Go to HOLD when TT-102 stays within 0.5 degC of setpoint for 60 s.

Timeout 1800 s. Raise alarm A-009 and go to DRAIN.

### 4.3 HOLD

Keep level, temperature and dosing running. Run the residence timer.

Go to DISCHARGE when the timer reaches 600 s. Operator range 300 to 3600 s.

### 4.4 DISCHARGE

Heater off. Dosing off. Raw pumps off. Close XV-101. Open XV-102.
Run P-102 at 60 percent.

Go to DRAIN when LT-102 falls to 300 mm.

Timeout 600 s. Raise alarm A-009.

### 4.5 DRAIN

Run P-102 at 100 percent.

Go to IDLE when LT-102 stays at or below 50 mm for 10 s. Close XV-102.

### 4.6 PAUSE

Entered when the operator presses Hold. Timers stop. FCV-101 closes. Heater goes
to 0 percent. Pumps stop.

Press Start to go back to the state it came from.

### 4.7 TRIP

Entered on any interlock in section 5.

All pumps off. Heater off. FCV-101 closed. XV-101 and XV-102 closed.

TRIP is latched. It clears only when the cause has gone and the operator presses
Reset.

### 4.8 Controlled stop

When the operator presses Abort, devices stop in this order:

1. Heater
2. Dosing
3. Pumps
4. Valves close

A trip is different. A trip drops everything at once.

---

## 5. Interlocks

Safety contacts are wired normally closed. Closed means healthy. A broken wire
opens the circuit and trips.

Interlocks are checked at the start of every scan, before the sequence and the
loops.

| # | Trips on | Sensed by | Result | Reset |
|---|---|---|---|---|
| I1 | Emergency stop pressed | ESD-01 | Everything off. A safety relay also drops the contactors without the PLC. | Manual |
| I2 | Raw tank empty | LSLL-101 | Raw pumps off | Auto, after 10 s |
| I3 | Treatment tank too full | LSHH-102 | Raw pumps off, XV-101 and FCV-101 closed | Auto |
| I4 | Too hot, 85 degC | TSHH-102 | Heater off. Also wired in series with the heater contactor. | Manual |
| I5 | Level below 800 mm | LT-102 | Heater blocked | Auto |
| I6 | Both raw pumps faulted | XA-101A and XA-101B | TRIP | Manual |
| I7 | Analog signal bad for 30 s | FB_AIN_SCALE | TRIP if LT-102 or TT-102 | Manual |
| I8 | Level not falling while the discharge pump runs, 20 s | LT-102 | P-102 off, XV-102 closed | Manual |

### 5.1 How interlocks are applied

POU_SAFETY does not switch any device on. It only gives permission. The rest of
the program has to ask for that permission first.

```
PERM_HEATER := ESD_OK AND TSHH_OK AND LT_VALID AND TT_VALID
               AND (LEVEL >= 800) AND NOT TRIPPED
```

The heater permission uses the measured level, not the sequence state. So a fault
in the sequence cannot switch the heater on in an empty tank.

I1 and I4 are also wired in hardware. They work whether or not the PLC is running.

---

## 6. Alarms

| Tag | Alarm | Priority | Reset |
|---|---|---|---|
| A-001 | Emergency stop | Critical | Manual |
| A-002 | Over temperature | Critical | Manual |
| A-003 | Both raw pumps failed | Critical | Manual |
| A-004 | Treatment tank too full | High | Auto |
| A-005 | Raw tank empty | High | Auto |
| A-006 | Duty pump failed, standby started | High | Manual |
| A-007 | Analog signal bad | High | Auto |
| A-008 | Signal not changing | Medium | Manual |
| A-009 | Sequence timeout | Medium | Manual |
| A-010 | Temperature more than 5 degC from setpoint | Medium | Auto |
| A-011 | Pump feedback does not match command | Medium | Manual |
| A-012 | Dosing more than 20 percent off setpoint | Low | Auto |

The alarm system records which alarm came first. One fault often sets off several
alarms, and the first one is usually the real cause.

Horn ALM-H sounds on a new alarm and is silenced by HS-04. Beacon ALM-B flashes
until the alarm is acknowledged, then stays on while the alarm is still active.

---

## 7. Reference documents

| Number | Title |
|---|---|
| WTS-100-CN-001 | Control narrative (this document) |
| WTS-100-DB-001 | Design basis |
| WTS-100-II-001 | Instrument index |
| WTS-100-PID-001 | P&ID |
| WTS-100-CAL-001 | Signal conditioning and calibration |
| WTS-100-FAT-001 | Factory acceptance test |
