# Instrument Index
## WTS-100 Water Treatment and Transfer Skid

A list of every sensor, valve and motor on the skid. 33 in total.

For each one: what it measures, its range, how it connects to the PLC, and what
it does when it fails.

---

## 1. How to read a tag

The first letter is what it measures. The letters after it are what it does.
The number is the loop it belongs to.

| Tag | Reads as |
|---|---|
| LT-102 | Level Transmitter, loop 102 |
| LSHH-102 | Level Switch High High, loop 102 |
| FCV-101 | Flow Control Valve, loop 101 |
| TSHH-102 | Temperature Switch High High, loop 102 |

Everything numbered 102 is on the treatment tank.

Common first letters: L level, F flow, T temperature, P pressure, A analysis,
Z position, X unclassified, H hand.

---

## 2. Analog inputs

Sensors that send a number. All are 4 to 20 mA.

| Tag | What it measures | Range | Type | PLC | If it fails |
|---|---|---|---|---|---|
| LT-101 | Raw tank level | 0 to 3000 mm | Guided wave radar | %IW0 | reads low |
| LT-102 | Treatment tank level | 0 to 2500 mm | Hydrostatic pressure | %IW2 | reads low |
| FT-101 | Water flow in | 0 to 50 m3/h | Electromagnetic | %IW4 | reads low |
| FT-103 | Chemical flow | 0 to 500 L/h | Coriolis | %IW6 | reads low |
| TT-102 | Treatment tank temperature | 0 to 100 degC | Pt100 with transmitter | %IW8 | reads high |
| PT-101 | Pump discharge pressure | 0 to 10 bar | Piezoresistive | %IW10 | reads low |
| AT-102 | Treated water conductivity | 0 to 2000 uS/cm | Toroidal | %IW12 | reads low |

---

## 3. Analog outputs

Devices the PLC drives to a position or a power level.

| Tag | What it drives | Range | PLC | If it fails |
|---|---|---|---|---|
| FCV-101 | Inlet valve position | 0 to 100 % | %QW0 | closes |
| HTR-101 | Heater power | 0 to 100 % | %QW2 | off |
| P-103 | Dosing pump speed | 0 to 100 % | %QW4 | off |
| P-102 | Discharge pump speed | 0 to 100 % | %QW6 | off |

---

## 4. Digital inputs

Switches and contacts. On or off only. NC means normally closed, which is the
healthy state. A broken wire opens the circuit and trips.

| Tag | What it is | Wiring | PLC |
|---|---|---|---|
| ESD-01 | Emergency stop | NC | %IX0.0 |
| LSLL-101 | Raw tank empty switch | NC | %IX0.1 |
| LSHH-102 | Treatment tank full switch | NC | %IX0.2 |
| TSHH-102 | Over temperature thermostat, 85 degC | NC | %IX0.3 |
| ZSO-101 | XV-101 open limit | NO | %IX0.4 |
| ZSC-101 | XV-101 closed limit | NO | %IX0.5 |
| XS-101A | Pump A running feedback | NO | %IX0.6 |
| XS-101B | Pump B running feedback | NO | %IX0.7 |
| XA-101A | Pump A overload tripped | NC | %IX1.0 |
| XA-101B | Pump B overload tripped | NC | %IX1.1 |
| HS-01 | Hand / Off / Auto switch | NO | %IX1.2 |
| HS-02 | Start button | NO | %IX1.3 |
| HS-03 | Stop button | NC | %IX1.4 |
| HS-04 | Alarm acknowledge | NO | %IX1.5 |

---

## 5. Digital outputs

Coils the PLC switches on or off. All fail off. Both valves spring closed.

| Tag | What it switches | PLC |
|---|---|---|
| MTR-101A | Pump A contactor | %QX0.0 |
| MTR-101B | Pump B contactor | %QX0.1 |
| MTR-102 | Discharge pump enable | %QX0.2 |
| XV-101 | Inlet valve | %QX0.3 |
| XV-102 | Discharge valve | %QX0.4 |
| HTR-EN | Heater contactor | %QX0.5 |
| ALM-H | Alarm horn | %QX0.6 |
| ALM-B | Alarm beacon | %QX0.7 |

---

## 6. Failure direction

Every sensor eventually fails. The direction it fails in is chosen, not accidental.

TT-102 fails high. A dead temperature sensor reads hot, so the heater switches off.

LT-102 fails low. A dead level sensor reads empty, so the pumps stop and the
heater is blocked.

Opposite directions on the same tank. There is no single safe direction. It
depends on what the reading is used for.

---

## 7. Why the treatment tank has two level devices

LT-102 is a transmitter. It gives a number, and it runs the process.

LSHH-102 is a switch. It gives yes or no, and it protects the tank.

They are separate hardware using different physics. If the transmitter sticks at
1800 mm while the tank keeps filling, the switch still stops the inflow.

One device must never do both control and protection. A single failure would then
remove both, and nobody would know.

TT-102 and TSHH-102 work the same way for temperature.

---

## 8. Range selection

Ranges match the process, not the pipe size and not a round number.

T-102 is 2500 mm tall, so LT-102 is ranged 0 to 2500 mm.

Ranging it 0 to 10000 mm to be safe would be worse. Accuracy is a percentage of
span, so a wider range than needed throws away resolution on the tank you have.

FT-101 is ranged 0 to 50 m3/h when normal flow is 30 m3/h. Enough headroom to see
a surge, not so much that normal running sits squashed at the bottom of the scale.

---

## 9. Signal count

| Type | Count |
|---|---|
| Analog input | 7 |
| Analog output | 4 |
| Digital input | 14 |
| Digital output | 8 |
| **Total** | **33** |

---

## 10. Reference documents

| Number | Title |
|---|---|
| WTS-100-CN-001 | Control narrative |
| WTS-100-DB-001 | Design basis |
| WTS-100-II-001 | Instrument index (this document) |
| WTS-100-PID-001 | P&ID |
