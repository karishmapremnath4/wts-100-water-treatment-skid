# WTS-100 Factory Acceptance Test, results

Run 2026-08-27 22:35   |   **14 of 14 passed**

Each case starts from a healthy running plant and breaks exactly one thing. Reference is the interlock or narrative section under test.

| # | Ref | Test | Expected | Actual | Result |
|---|---|---|---|---|---|
| FAT-01 | I1 | Emergency stop removes every permission and trips | all three permissions FALSE, trip latched, first out I1, heater and pumps off | `trip=True perms=[False, False, False] first_out=1` | PASS |
| FAT-02 | I1 | Trip stays latched after the cause clears | trip remains TRUE when the e-stop is released | `trip still True after cause cleared` | PASS |
| FAT-03 | I1 | Reset only works once the cause has gone | reset with cause present has no effect, reset after clearing works | `reset with cause present trip=True, after clearing trip=False` | PASS |
| FAT-04 | I2 | Raw tank low low stops the pumps | perm_pumps FALSE, pump contactor off | `perm_pumps=False MTR_101A=False` | PASS |
| FAT-05 | I3 | Treatment tank high high stops all inflow | perm_pumps and perm_inlet FALSE, XV-101 closed | `perm_pumps=False perm_inlet=False XV_101=False` | PASS |
| FAT-06 | I5 | Low level blocks the heater but NOT the pumps | perm_heater FALSE, heater off, perm_pumps still TRUE so the tank can refill | `perm_heater=False HTR_EN=False perm_pumps=True` | PASS |
| FAT-07 | I7 | Broken level transmitter blocks the heater | perm_heater FALSE, heater off | `perm_heater=False HTR_EN=False` | PASS |
| FAT-08 | 5 | One pump fault changes over to the standby without tripping | no trip, P-101B running, P-101A stopped | `trip=False MTR_101A=False MTR_101B=True` | PASS |
| FAT-09 | I6 | Both pumps faulted trips the plant | trip latched, first out I6, all permissions FALSE | `trip=True first_out=6 perms=[False, False, False]` | PASS |
| FAT-10 | 4.1 | Sequence advances FILL to HEAT at 1200 mm | state is HEAT once the level passes 1200 mm | `state=HEAT at 1250 mm` | PASS |
| FAT-11 | I4 | Over temperature blocks the heater and trips | perm_heater FALSE, trip latched, first out I4 | `perm_heater=False trip=True first_out=4` | PASS |
| FAT-12 | 4.8 | Controlled stop shuts down in the correct order | state IDLE, heater off, pumps off, valves closed | `state=IDLE HTR_EN=False MTR_101A=False XV_101=False` | PASS |
| FAT-13 | I8 | Blocked discharge stops the discharge pump | P-102 driven to 0 percent when the level stops falling for 20 s | `state=HEAT P_102=0% XV_102=False` | PASS |
| FAT-14 | A-008 | Frozen transmitter raises an alarm but does NOT trip | A-008 active, no trip, because a steady process can also read steady | `A-008=True trip=False perm_heater=True` | PASS |


## Witness

| | |
|---|---|
| Tested by | K. Premnath |
| Witnessed by | (open) |
| Date | 2026-08-27 |
