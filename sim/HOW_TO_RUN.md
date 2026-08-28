# How to run WTS-100

Three programs, three terminal windows, one browser tab.
Each program keeps running and holds its own window, so they cannot share one.

---

## ONE TIME ONLY

Install the Modbus library. You have already done this.

```
pip3 install pymodbus
```

---

## STEP 1   the plant

Open Terminal. Paste this and press Enter.

```
cd sim && python3 plant_server.py --speed 10
```

You should see:

```
WTS-100 plant simulator on 127.0.0.1:5020   speed x10.0
  input regs  30001+  analog in    discrete in 10001+  switches
  holding     40001+  analog out   coils       00001+  motors and valves
```

Then it goes quiet. That is correct, it is waiting for the controller.

**Leave this window alone. Do not type in it.**

---

## STEP 2   the HMI

Press **Cmd + N** for a NEW window. Paste this.

```
cd sim && python3 hmi.py
```

You should see:

```
WTS-100 operator interface on http://127.0.0.1:8080
Ctrl+C to stop
```

**Leave this window alone too.**

---

## STEP 3   open the browser

In Chrome, go to:

```
http://127.0.0.1:8080
```

The screen appears but says NO DATA. That is correct, nothing is controlling
the plant yet.

---

## STEP 4   the controller

Press **Cmd + N** for a THIRD window. Paste this.

```
cd sim && python3 plc.py --seconds 420 --speed 10
```

A live table starts printing. **Now watch the browser**, it comes alive within
a second.

---

## TO STOP

Press **Ctrl + C** in each of the three windows.

---

## WHAT YOU SHOULD SEE

| Time | What happens |
|---|---|
| straight away | STATE goes IDLE to FILL, tank starts filling |
| about 30 s | pump P-101A circle turns solid black |
| level 1200 mm | STATE goes FILL to HEAT |
| just after | valve percentage drops as the cascade takes over |
| | HTR shows 100% and the heater element turns red |
| about 4 min | temperature reaches 45 degC, STATE goes to HOLD |
| after that | DISCHARGE, level falls, then DRAIN, then IDLE |

---

## COMMON MISTAKES

**Typing the second command into the first window.**
That window is busy running the plant. Nothing you type there will run.
Always Cmd + N first.

**Pasting the http address into Terminal.**
`http://127.0.0.1:8080` goes in the browser, not the terminal.

**Forgetting the quotes.**
The folder name has spaces in it. Without quotes the shell reads it as three
separate arguments and fails.

**Raising the speed above 10.**
At higher speeds each scan advances more process time than the 3 second pump
feedback timer, so both pumps fault immediately and the plant trips. Keep it
at 10 or below.

**Starting the controller twice without restarting the plant.**
The plant keeps its state, so the tank is still full from the last run and it
will jump to HEAT in two seconds. For a clean batch, restart all three.

---

## WHAT THE OPTIONS MEAN

| Option | Meaning |
|---|---|
| `--speed 10` | Run the process 10 times faster than real life. A 45 minute heat up takes about 4.5 minutes. **The plant and the controller must use the same number.** |
| `--seconds 420` | How long the controller runs. 420 is enough for a full batch. |
| `--no-log` | Do not write the CSV or status.json. Leave this off, the HMI needs status.json. |

---

## TO SAVE THE OUTPUT

```
python3 plc.py --seconds 420 --speed 10 | tee run.log
```

`tee` prints to the screen and writes `run.log` at the same time.

The controller also writes `batch_YYYYMMDD_HHMMSS.csv` automatically on every
run, one row per second, 28 columns. That is the historian, and it is the
evidence the FAT is signed off against.

---

## THE FILES

| File | What it is |
|---|---|
| `plant.py` | The plant model. Tank levels, heat balance, valve and pump lag, sensor noise |
| `modbus_map.py` | Which register holds what, and the 4-20 mA counts conversion from document 04 |
| `plant_server.py` | Serves the plant over Modbus TCP on 127.0.0.1:5020 |
| `plc.py` | The controller. Safety, pumps, control loops, sequence, alarms |
| `historian.py` | Logs every scan to CSV and writes status.json for the HMI |
| `hmi.py` | The operator interface on port 8080 |
