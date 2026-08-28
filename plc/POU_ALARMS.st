(*
    WTS-100  POU_ALARMS
    Alarm management.  IEC 61131-3 Structured Text.

    Implements section 6 of the control narrative, to ISA-18.2.

    FIRST OUT
    One fault usually sets off several alarms.  Supply fails, so the pump
    stops, so flow falls, so level drops, so temperature deviates.  Five
    alarms, one cause.  FIRST_OUT records whichever came first while no alarm
    was already standing, because that is the one that actually broke.
    Without it an operator at 3 a.m. faces a screen of alarms with no way to
    tell cause from consequence.

    PRIORITY
    Set by consequence and by how fast the operator must react.
    If everything is critical then nothing is.
*)

FUNCTION_BLOCK POU_ALARMS

VAR_INPUT
    ESD_01_OK       : BOOL;
    TSHH_102_OK     : BOOL;
    LSHH_102_OK     : BOOL;
    LSLL_101_OK     : BOOL;
    BOTH_PUMPS_FAIL : BOOL;
    DUTY_CHANGEOVER : BOOL;
    AIN_INVALID     : BOOL;
    AIN_STUCK       : BOOL;
    SEQ_TIMEOUT     : BOOL;
    TEMP_DEVIATION  : BOOL;
    PUMP_FB_MISMATCH: BOOL;
    DOSE_DEVIATION  : BOOL;
    ACK_CMD         : BOOL;
END_VAR

VAR_OUTPUT
    ALM_001 : BOOL;   (* emergency stop            Critical *)
    ALM_002 : BOOL;   (* over temperature          Critical *)
    ALM_003 : BOOL;   (* both raw pumps failed     Critical *)
    ALM_004 : BOOL;   (* treatment tank too full   High     *)
    ALM_005 : BOOL;   (* raw tank empty            High     *)
    ALM_006 : BOOL;   (* duty pump failed          High     *)
    ALM_007 : BOOL;   (* analog signal bad         High     *)
    ALM_008 : BOOL;   (* signal not changing       Medium   *)
    ALM_009 : BOOL;   (* sequence timeout          Medium   *)
    ALM_010 : BOOL;   (* temperature deviation     Medium   *)
    ALM_011 : BOOL;   (* pump feedback mismatch    Medium   *)
    ALM_012 : BOOL;   (* dosing deviation          Low      *)

    ANY_ALARM       : BOOL;
    ANY_UNACK       : BOOL;
    FIRST_OUT_ID    : INT;    (* 0 none, else 1..12 *)
    HIGHEST_PRIORITY: INT;    (* 0 none, 1 Critical, 2 High, 3 Medium, 4 Low *)
    ALM_HORN        : BOOL;
    ALM_BEACON      : BOOL;
END_VAR

VAR
    acked       : BOOL;
    prev_any    : BOOL;
    beacon_tick : TON;
END_VAR


(* --- alarm conditions --------------------------------------------------- *)
ALM_001 := NOT ESD_01_OK;
ALM_002 := NOT TSHH_102_OK;
ALM_003 := BOTH_PUMPS_FAIL;
ALM_004 := NOT LSHH_102_OK;
ALM_005 := NOT LSLL_101_OK;
ALM_006 := DUTY_CHANGEOVER;
ALM_007 := AIN_INVALID;
ALM_008 := AIN_STUCK;
ALM_009 := SEQ_TIMEOUT;
ALM_010 := TEMP_DEVIATION;
ALM_011 := PUMP_FB_MISMATCH;
ALM_012 := DOSE_DEVIATION;

ANY_ALARM := ALM_001 OR ALM_002 OR ALM_003 OR ALM_004 OR ALM_005 OR ALM_006
          OR ALM_007 OR ALM_008 OR ALM_009 OR ALM_010 OR ALM_011 OR ALM_012;


(* --- first out.
   --- Only captured when nothing was already standing, otherwise a later
   --- consequence would overwrite the real root cause.                  --- *)
IF ANY_ALARM AND (FIRST_OUT_ID = 0) THEN
    IF      ALM_001 THEN FIRST_OUT_ID := 1;
    ELSIF   ALM_002 THEN FIRST_OUT_ID := 2;
    ELSIF   ALM_003 THEN FIRST_OUT_ID := 3;
    ELSIF   ALM_004 THEN FIRST_OUT_ID := 4;
    ELSIF   ALM_005 THEN FIRST_OUT_ID := 5;
    ELSIF   ALM_006 THEN FIRST_OUT_ID := 6;
    ELSIF   ALM_007 THEN FIRST_OUT_ID := 7;
    ELSIF   ALM_008 THEN FIRST_OUT_ID := 8;
    ELSIF   ALM_009 THEN FIRST_OUT_ID := 9;
    ELSIF   ALM_010 THEN FIRST_OUT_ID := 10;
    ELSIF   ALM_011 THEN FIRST_OUT_ID := 11;
    ELSIF   ALM_012 THEN FIRST_OUT_ID := 12;
    END_IF;
END_IF;

IF NOT ANY_ALARM THEN
    FIRST_OUT_ID := 0;
END_IF;


(* --- highest standing priority ------------------------------------------ *)
IF   ALM_001 OR ALM_002 OR ALM_003                        THEN HIGHEST_PRIORITY := 1;
ELSIF ALM_004 OR ALM_005 OR ALM_006 OR ALM_007            THEN HIGHEST_PRIORITY := 2;
ELSIF ALM_008 OR ALM_009 OR ALM_010 OR ALM_011            THEN HIGHEST_PRIORITY := 3;
ELSIF ALM_012                                             THEN HIGHEST_PRIORITY := 4;
ELSE                                                           HIGHEST_PRIORITY := 0;
END_IF;


(* --- acknowledge.
   --- A NEW alarm clears the acknowledgement, so the horn sounds again
   --- rather than staying silent because an earlier one was acked.      --- *)
IF ANY_ALARM AND NOT prev_any THEN
    acked := FALSE;
END_IF;
prev_any := ANY_ALARM;

IF ACK_CMD THEN
    acked := TRUE;
END_IF;

IF NOT ANY_ALARM THEN
    acked := FALSE;
END_IF;

ANY_UNACK := ANY_ALARM AND NOT acked;


(* --- annunciation.
   --- Horn on any unacknowledged alarm.
   --- Beacon flashes while unacknowledged, steady once acked but still
   --- standing, so a glance tells you both things at once.              --- *)
ALM_HORN := ANY_UNACK;

beacon_tick(IN := NOT beacon_tick.Q, PT := T#500ms);
IF ANY_UNACK THEN
    ALM_BEACON := beacon_tick.Q;
ELSIF ANY_ALARM THEN
    ALM_BEACON := TRUE;
ELSE
    ALM_BEACON := FALSE;
END_IF;

END_FUNCTION_BLOCK
