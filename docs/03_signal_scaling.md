# Signal Scaling and Calibration
## WTS-100 Water Treatment and Transfer Skid

How a sensor reading becomes a number the PLC can use, and how to tell when
that number has gone bad.

The block FB_AIN_SCALE in the PLC program implements this document.

---

## 1. Why 4 to 20 mA

Transmitters send a current, not a voltage. 4 mA is the bottom of the range,
20 mA is the top.

**Cable length does not matter.** In a series loop the current is the same at
every point. A voltage signal drops across the resistance of a long cable and
reads low at the far end.

**A broken wire is detectable.** Empty reads 4 mA, not 0 mA. So 0 mA can only
mean something is broken. If the signal were 0 to 10 V, a cut wire would read
0 V, which looks exactly like a real zero reading. You would never know.

This is called a live zero.

### Loop voltage check, worst case

| Item | Volts |
|---|---|
| Transmitter minimum operating voltage | 12.0 |
| Sense resistor 250 ohm at 20 mA | 5.0 |
| Barrier and terminal drops | 1.5 |
| Cable, 2 x 100 m at 0.09 ohm/m, 20 mA | 0.4 |
| **Total needed** | **18.9** |
| Supply | 24.0 |
| **Spare** | **5.1** |

Passes with margin.

---

## 2. Counts

The analog input card turns the current into a whole number.

| Current | Counts | Meaning |
|---|---|---|
| below 3.6 mA | below -691 | broken wire or dead transmitter |
| 4.000 mA | 0 | 0 percent |
| 12.000 mA | 13824 | 50 percent |
| 20.000 mA | 27648 | 100 percent |
| above 20.5 mA | above 28512 | transmitter failed high or short circuit |

There are 1728 counts per milliamp.

### The formula

```
value in engineering units = EU_min + (counts / 27648) x (EU_max - EU_min)
```

For an analog output, the same thing backwards:

```
counts = (value - EU_min) / (EU_max - EU_min) x 27648
```

---

## 3. Scaling for each instrument

| Tag | Range | Counts per unit | Smallest step |
|---|---|---|---|
| LT-101 | 0 to 3000 mm | 9.216 | 0.109 mm |
| LT-102 | 0 to 2500 mm | 11.059 | 0.090 mm |
| FT-101 | 0 to 50 m3/h | 552.96 | 0.0018 m3/h |
| FT-103 | 0 to 500 L/h | 55.296 | 0.018 L/h |
| TT-102 | 0 to 100 degC | 276.48 | 0.0036 degC |
| PT-101 | 0 to 10 bar | 2764.8 | 0.0004 bar |
| AT-102 | 0 to 2000 uS/cm | 13.824 | 0.072 uS/cm |

The card can resolve far finer than any of these sensors can measure. That is
the right way round. The measurement is limited by the instrument, not by the
card.

---

## 4. How accurate the reading actually is

Errors from different sources are independent, so they are combined as a root
sum of squares rather than simply added.

```
total = square root of ( sensor^2 + transmitter^2 + card^2 + drift^2 )
```

### Temperature, TT-102

| Source | Error |
|---|---|
| Pt100 Class A sensor at 50 degC | 0.25 degC |
| Head transmitter | 0.10 degC |
| Analog card | 0.007 degC |
| Ambient drift over a 20 degC swing | 0.20 degC |
| **Combined** | **0.34 degC** |

**This is why the temperature deadband is 0.5 degC.** The controller cannot
tell the difference between a real change and measurement noise below about
0.34 degC. A tighter deadband would make it react to noise instead of to the
process. 0.5 degC sits just outside the uncertainty, at about 1.5 times it.

The deadband was calculated, not chosen.

### Flow, FT-101

| Source | Error |
|---|---|
| Magnetic flowmeter, 0.5 percent of reading | 0.25 m3/h at full flow |
| Transmitter | 0.05 m3/h |
| Analog card | 0.004 m3/h |
| **Combined** | **0.255 m3/h, or 0.51 percent of span** |

Note this is a percentage of the reading, not of the range. At 10 m3/h the
absolute error falls to about 0.05 m3/h. Below 1.0 m3/h the reading is mostly
noise, so it is forced to zero.

---

## 5. When a reading goes bad

| Problem | How it is spotted | What the PLC does |
|---|---|---|
| Broken wire | counts below -691 | mark invalid, hold the last good value, alarm |
| Transmitter failed high | counts above 28512 | mark invalid, clamp to full scale, alarm |
| Reading frozen | value has not moved at all for 5 minutes while the process should be changing | alarm only, do not trip |

**Why hold the last good value instead of dropping to zero.** A control loop
fed a sudden zero would slam its output to the limit. Holding the last good
value keeps the plant steady and gives the sequence 30 seconds to shut down in
a controlled way. That is interlock I7 in the control narrative.

**Why a frozen reading only alarms.** A steady process legitimately produces a
steady reading. A frozen signal is a reason to go and look, not a reason to
trip.

A frozen sensor is the dangerous case, because the reading stays inside the
valid range and looks perfectly healthy. Range checks alone will never catch it.

---

## 6. Calibration

Done at commissioning and once a year. Each loop is calibrated as a whole loop:
inject at the transmitter, read the value on the HMI. Not at the card. That way
a wiring fault and a scaling fault are both caught.

For each analog input:

1. Isolate the instrument and connect a calibrated current source in its place.
2. Inject 4, 8, 12, 16 and 20 mA in turn. That is 0, 25, 50, 75 and 100 percent.
3. Write down what the HMI shows at each point.
4. Work out the error as a percentage of span. It must be inside the figure
   from section 4.
5. Repeat going back down, 20 to 4 mA, to catch hysteresis.
6. Record the results. A loop that fails is tagged and not commissioned.

Record both as found and as left. As found tells you whether the loop has
drifted since last time. As left proves it is correct now.

### Zero and span

Zero moves the whole line up or down. Adjust it at 4 mA.

Span changes the slope of the line. Adjust it at 20 mA.

They interact, so always go back and check zero after adjusting span, and
repeat until both are right.
