(*
    WTS-100  POU_SAFETY
    Interlocks and permissives.  IEC 61131-3 Structured Text.

    This is the same logic as the ladder drawing drawings/ladder_safety.svg, written as
    text so it can be pasted straight into OpenPLC Editor and compiled.

    Runs FIRST in the scan, before the sequence and the loops, so nothing
    downstream can command an output this block has inhibited.

    All discrete safety contacts are wired normally closed.  Healthy = TRUE.
    A broken wire reads FALSE and therefore trips.

    Logic verified by test_ladder.py, 16 cases.
*)

FUNCTION_BLOCK POU_SAFETY

VAR_INPUT
    ESD_01_OK       : BOOL;   (* emergency stop not pressed      *)
    TSHH_102_OK     : BOOL;   (* below the 85 degC thermostat    *)
    XA_101A_OK      : BOOL;   (* pump A overload healthy         *)
    XA_101B_OK      : BOOL;   (* pump B overload healthy         *)
    LSLL_101_OK     : BOOL;   (* raw tank not at low low         *)
    LSHH_102_OK     : BOOL;   (* treat tank not at high high     *)
    LT_102_VALID    : BOOL;   (* level reading trustworthy       *)
    TT_102_VALID    : BOOL;   (* temperature reading trustworthy *)
    LT_102_MM       : REAL;   (* scaled treatment tank level     *)
    HS_04_RESET     : BOOL;   (* reset pushbutton                *)
END_VAR

VAR_OUTPUT
    PERM_RAW_PUMPS  : BOOL;
    PERM_HEATER     : BOOL;
    PERM_INLET      : BOOL;
    TRIP            : BOOL;
    TRIP_CAUSE      : BOOL;
    FIRST_OUT       : INT;    (* 0 none, else the interlock number *)
END_VAR

VAR
    ain_timer   : TON;
    AIN_FAULT   : BOOL;
    LVL_OK      : BOOL;
END_VAR

VAR CONSTANT
    LVL_HEATER_MIN : REAL := 800.0;
END_VAR


(* --- analog fault, interlock I7.  30 s so a brief glitch is ridden out --- *)
ain_timer(IN := NOT (LT_102_VALID AND TT_102_VALID), PT := T#30s);
AIN_FAULT := ain_timer.Q;

LVL_OK := (LT_102_MM >= LVL_HEATER_MIN);


(* --- RUNG 1  trip causes.  These are ALTERNATIVES, so OR not AND.       ---
   --- The two pump overloads are ANDed, because one failed pump changes  ---
   --- over to the standby and does not trip the plant.                   --- *)
TRIP_CAUSE :=  (NOT ESD_01_OK)
            OR (NOT TSHH_102_OK)
            OR ((NOT XA_101A_OK) AND (NOT XA_101B_OK))
            OR AIN_FAULT;


(* --- RUNG 2 and 3  latch and reset.
   --- Reset only clears the trip when the cause has already gone.        --- *)
IF TRIP_CAUSE THEN
    TRIP := TRUE;
    IF FIRST_OUT = 0 THEN
        IF    NOT ESD_01_OK                             THEN FIRST_OUT := 1;
        ELSIF NOT TSHH_102_OK                           THEN FIRST_OUT := 4;
        ELSIF (NOT XA_101A_OK) AND (NOT XA_101B_OK)     THEN FIRST_OUT := 6;
        ELSIF AIN_FAULT                                 THEN FIRST_OUT := 7;
        END_IF;
    END_IF;
ELSIF HS_04_RESET THEN
    TRIP      := FALSE;
    FIRST_OUT := 0;
END_IF;


(* --- RUNG 4  permission to run the raw water pumps.  I2 and I3.        --- *)
PERM_RAW_PUMPS := ESD_01_OK AND LSLL_101_OK AND LSHH_102_OK AND NOT TRIP;

(* --- RUNG 5  permission to run the heater.  I4 and I5.
   --- The level test uses the MEASURED level, never the sequence state,  ---
   --- so a defect in the sequence cannot fire a dry element.             --- *)
PERM_HEATER := ESD_01_OK AND TSHH_102_OK AND LT_102_VALID
               AND TT_102_VALID AND LVL_OK AND NOT TRIP;

(* --- RUNG 6  permission to open the inlet.  I3.                        --- *)
PERM_INLET := ESD_01_OK AND LSHH_102_OK AND NOT TRIP;

END_FUNCTION_BLOCK
