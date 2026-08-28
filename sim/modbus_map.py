#!/usr/bin/env python3
"""WTS-100 Modbus register map and analog conversion.

The plant is a Modbus TCP server.  The controller is the client.  This module
is the single definition of which register holds what, shared by both sides so
they cannot drift apart.

Analog values cross the link as RAW COUNTS, not engineering units, exactly as
they would from a real 4-20 mA input card.  Converting counts to millimetres is
the controller's job, and it uses the same numbers as document 04:

      4.000 mA ->      0 counts
     20.000 mA ->  27648 counts
     below 3.6 mA  (< -691)  -> wire break
     above 20.5 mA (> 28512) -> transmitter failed high

Register layout
    input registers   30001+   analog inputs   (sensors, read only)
    holding registers 40001+   analog outputs  (commands)
    discrete inputs   10001+   digital inputs  (switches, read only)
    coils             00001+   digital outputs (commands)
"""

FULL_SCALE = 27648.0
LO_FAULT   = -691       # 3.6 mA
HI_FAULT   =  28512     # 20.5 mA

# ---------------------------------------------------------------- analog in
# name -> (register index, EU min, EU max)
AI = {
    "LT_101": (0, 0.0, 3000.0),
    "LT_102": (1, 0.0, 2500.0),
    "FT_101": (2, 0.0,   50.0),
    "FT_103": (3, 0.0,  500.0),
    "TT_102": (4, 0.0,  100.0),
    "PT_101": (5, 0.0,   10.0),
    "AT_102": (6, 0.0, 2000.0),
}

# ---------------------------------------------------------------- analog out
AO = {
    "FCV_101": (0, 0.0, 100.0),
    "HTR_101": (1, 0.0, 100.0),
    "P_103":   (2, 0.0, 100.0),
    "P_102":   (3, 0.0, 100.0),
}

# ---------------------------------------------------------------- discrete in
DI = {
    "ESD_01_OK":   0,
    "LSLL_101_OK": 1,
    "LSHH_102_OK": 2,
    "TSHH_102_OK": 3,
    "XA_101A_OK":  4,
    "XA_101B_OK":  5,
    "XS_101A":     6,
    "XS_101B":     7,
}

# ---------------------------------------------------------------- coils
DO = {
    "MTR_101A": 0,
    "MTR_101B": 1,
    "XV_101":   2,
    "XV_102":   3,
    "HTR_EN":   4,
    "MTR_102":  5,
    "ALM_H":    6,
    "ALM_B":    7,
}


def eu_to_counts(value, eu_min, eu_max):
    """Engineering units to raw counts, clamped to the valid span."""
    frac = (value - eu_min) / (eu_max - eu_min)
    return int(max(0.0, min(1.0, frac)) * FULL_SCALE)


def counts_to_eu(counts, eu_min, eu_max):
    """Raw counts to engineering units, with validity.

    Returns (value, valid).  On a fault the value is the clamped edge of span
    and valid is False, so the caller decides what to do rather than silently
    acting on a bad number.
    """
    if counts < LO_FAULT:
        return eu_min, False              # wire break
    if counts > HI_FAULT:
        return eu_max, False              # failed high
    frac = max(0.0, min(1.0, counts / FULL_SCALE))
    return eu_min + frac * (eu_max - eu_min), True


def encode_ai(readings):
    """Plant readings in EU -> list of counts, ordered by register index."""
    out = [0] * len(AI)
    for name, (idx, lo, hi) in AI.items():
        v = readings[name]
        # a broken transmitter is modelled as a negative reading in plant.py
        out[idx] = LO_FAULT - 100 if v < -1.0 else eu_to_counts(v, lo, hi)
    return out


def decode_ai(counts_list):
    """List of counts -> {name: (value, valid)}."""
    return {name: counts_to_eu(counts_list[idx], lo, hi)
            for name, (idx, lo, hi) in AI.items()}
