FUNCTION_BLOCK pou_safety
  VAR_INPUT
    ESD_01_OK : BOOL;
    TSHH_102_OK : BOOL;
    XA_101A_OK : BOOL;
    XA_101B_OK : BOOL;
    LSLL_101_OK : BOOL;
    LSHH_102_OK : BOOL;
    LT_102_VALID : BOOL;
    TT_102_VALID : BOOL;
    LT_102_MM : REAL;
    HS_04_RESET : BOOL;
  END_VAR
  VAR_OUTPUT
    PERM_RAW_PUMPS : BOOL;
    PERM_HEATER : BOOL;
    PERM_INLET : BOOL;
    TRIP : BOOL;
    TRIP_CAUSE : BOOL;
    FIRST_OUT : INT;
  END_VAR

(* RUNG 1  trip causes.  These are ALTERNATIVES, so OR not AND.
   The two pump overloads are ANDed, because one failed pump changes over
   to the standby and must not trip the plant. *)
TRIP_CAUSE :=  (NOT ESD_01_OK)
            OR (NOT TSHH_102_OK)
            OR ((NOT XA_101A_OK) AND (NOT XA_101B_OK));

(* RUNG 2 and 3  latch and reset.  Reset only clears once the cause has gone. *)
IF TRIP_CAUSE THEN
    TRIP := TRUE;
    IF FIRST_OUT = 0 THEN
        IF    NOT ESD_01_OK                         THEN FIRST_OUT := 1;
        ELSIF NOT TSHH_102_OK                       THEN FIRST_OUT := 4;
        ELSIF (NOT XA_101A_OK) AND (NOT XA_101B_OK) THEN FIRST_OUT := 6;
        END_IF;
    END_IF;
ELSIF HS_04_RESET THEN
    TRIP := FALSE;
    FIRST_OUT := 0;
END_IF;

(* RUNG 4  raw water pumps.  I2 dry run, I3 overfill. *)
PERM_RAW_PUMPS := ESD_01_OK AND LSLL_101_OK AND LSHH_102_OK AND NOT TRIP;

(* RUNG 5  heater.  I4 over temperature, I5 low level.
   Uses the MEASURED level, never the sequence state, so a defect in the
   sequence cannot fire a dry element. *)
PERM_HEATER := ESD_01_OK AND TSHH_102_OK AND LT_102_VALID
               AND TT_102_VALID AND (LT_102_MM >= 800.0) AND NOT TRIP;

(* RUNG 6  inlet.  I3 overfill. *)
PERM_INLET := ESD_01_OK AND LSHH_102_OK AND NOT TRIP;

END_FUNCTION_BLOCK