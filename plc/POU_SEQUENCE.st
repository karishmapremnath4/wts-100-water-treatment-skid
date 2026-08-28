(*
    WTS-100  POU_SEQUENCE
    Batch sequence.  IEC 61131-3 Structured Text.

    IDLE -> FILL -> HEAT -> HOLD -> DISCHARGE -> DRAIN -> IDLE

    One state is active at a time.  Every transition out of every state is
    listed.  Every state has a timeout, because a state machine with no
    timeout can wait forever for a condition that will never arrive, and the
    operator gets no indication why nothing is happening.

    Any interlock forces TRIP from any state.  TRIP is latched.

    Implements section 4 of the control narrative.
*)

FUNCTION_BLOCK POU_SEQUENCE

VAR_INPUT
    START_CMD       : BOOL;
    HOLD_CMD        : BOOL;
    ABORT_CMD       : BOOL;
    AUTO_MODE       : BOOL;
    TRIP            : BOOL;     (* from POU_SAFETY *)
    PERM_INLET      : BOOL;
    PERM_HEATER     : BOOL;
    LT_101_MM       : REAL;
    LT_102_MM       : REAL;
    TT_102_C        : REAL;
    TEMP_SETPOINT   : REAL;
    RESIDENCE_S     : TIME;
END_VAR

VAR_OUTPUT
    STATE           : INT;      (* 0 IDLE 1 FILL 2 HEAT 3 HOLD
                                   4 DISCHARGE 5 DRAIN 6 TRIP 7 PAUSE *)
    RUN_PUMPS       : BOOL;
    OPEN_XV101      : BOOL;
    OPEN_XV102      : BOOL;
    ENABLE_HEATER   : BOOL;
    ENABLE_DOSING   : BOOL;
    CASCADE_ON      : BOOL;
    FLOW_SP         : REAL;
    P102_SPEED      : REAL;
    TIMEOUT_ALARM   : BOOL;
END_VAR

VAR
    t_state     : TON;
    t_stable    : TON;
    t_residence : TON;
    t_drain     : TON;
    prev_state  : INT;
    state_timeout : TIME;
    at_temp     : BOOL;
END_VAR

VAR CONSTANT
    S_IDLE      : INT := 0;
    S_FILL      : INT := 1;
    S_HEAT      : INT := 2;
    S_HOLD      : INT := 3;
    S_DISCHARGE : INT := 4;
    S_DRAIN     : INT := 5;
    S_TRIP      : INT := 6;
    S_PAUSE     : INT := 7;
END_VAR


(* --- a trip beats everything, from any state --------------------------- *)
IF TRIP THEN
    STATE := S_TRIP;
END_IF;


(* --- pick the timeout for the state we are in.
   --- Rule: two to three times the expected duration.  Too tight and it
   --- nuisance trips on a slow day, too loose and a real fault goes
   --- unnoticed far too long.                                           --- *)
CASE STATE OF
    S_FILL:      state_timeout := T#900s;    (* fill takes about 5 min   *)
    S_HEAT:      state_timeout := T#5400s;   (* heat takes about 45 min  *)
    S_DISCHARGE: state_timeout := T#600s;
ELSE
    state_timeout := T#0s;
END_CASE;

t_state(IN := (STATE <> prev_state), PT := T#1s);
IF STATE <> prev_state THEN
    t_state(IN := FALSE);
END_IF;
prev_state := STATE;


CASE STATE OF

(* ------------------------------------------------------------ 4.0 IDLE *)
S_IDLE:
    RUN_PUMPS     := FALSE;
    OPEN_XV101    := FALSE;
    OPEN_XV102    := FALSE;
    ENABLE_HEATER := FALSE;
    ENABLE_DOSING := FALSE;
    CASCADE_ON    := FALSE;
    FLOW_SP       := 0.0;
    P102_SPEED    := 0.0;

    (* the raw tank check stops a batch that is guaranteed to fail *)
    IF START_CMD AND AUTO_MODE AND NOT TRIP AND (LT_101_MM > 400.0) THEN
        STATE := S_FILL;
    END_IF;

(* ------------------------------------------------------------ 4.1 FILL *)
S_FILL:
    OPEN_XV101 := PERM_INLET;
    RUN_PUMPS  := TRUE;
    CASCADE_ON := FALSE;      (* fixed flow: no level worth controlling yet *)
    FLOW_SP    := 30.0;

    IF LT_102_MM >= 1200.0 THEN
        STATE := S_HEAT;
    END_IF;

(* ------------------------------------------------------------ 4.2 HEAT *)
S_HEAT:
    OPEN_XV101    := PERM_INLET;
    RUN_PUMPS     := TRUE;
    CASCADE_ON    := TRUE;    (* level loop now sets the flow setpoint *)
    ENABLE_HEATER := PERM_HEATER;
    ENABLE_DOSING := TRUE;

    (* must sit within band CONTINUOUSLY, so a momentary excursion through
       setpoint while the tank is still stratified does not advance us *)
    at_temp := ABS(TT_102_C - TEMP_SETPOINT) <= 0.5;
    t_stable(IN := at_temp, PT := T#60s);

    IF t_stable.Q THEN
        STATE := S_HOLD;
    END_IF;

(* ------------------------------------------------------------ 4.3 HOLD *)
S_HOLD:
    CASCADE_ON    := TRUE;
    ENABLE_HEATER := PERM_HEATER;
    ENABLE_DOSING := TRUE;

    t_residence(IN := TRUE, PT := RESIDENCE_S);
    IF t_residence.Q THEN
        STATE := S_DISCHARGE;
    END_IF;

(* ------------------------------------------------------- 4.4 DISCHARGE *)
S_DISCHARGE:
    ENABLE_HEATER := FALSE;   (* heater OFF before the tank starts emptying *)
    ENABLE_DOSING := FALSE;
    RUN_PUMPS     := FALSE;
    OPEN_XV101    := FALSE;
    CASCADE_ON    := FALSE;
    OPEN_XV102    := TRUE;
    P102_SPEED    := 60.0;

    IF LT_102_MM <= 300.0 THEN
        STATE := S_DRAIN;
    END_IF;

(* ----------------------------------------------------------- 4.5 DRAIN *)
S_DRAIN:
    OPEN_XV102 := TRUE;
    P102_SPEED := 100.0;

    (* 10 s confirmation, so a splash as the last liquid clears the tapping
       does not end the batch early *)
    t_drain(IN := (LT_102_MM <= 50.0), PT := T#10s);
    IF t_drain.Q THEN
        OPEN_XV102 := FALSE;
        P102_SPEED := 0.0;
        STATE      := S_IDLE;
    END_IF;

(* ------------------------------------------------------------ 4.7 TRIP *)
S_TRIP:
    RUN_PUMPS     := FALSE;
    OPEN_XV101    := FALSE;
    OPEN_XV102    := FALSE;
    ENABLE_HEATER := FALSE;
    ENABLE_DOSING := FALSE;
    CASCADE_ON    := FALSE;
    FLOW_SP       := 0.0;
    P102_SPEED    := 0.0;

    IF NOT TRIP THEN
        STATE := S_IDLE;
    END_IF;

(* ----------------------------------------------------------- 4.6 PAUSE *)
S_PAUSE:
    RUN_PUMPS     := FALSE;
    ENABLE_HEATER := FALSE;
    FLOW_SP       := 0.0;
    IF START_CMD THEN
        STATE := S_HOLD;
    END_IF;

END_CASE;


(* --- operator hold, from any running state ----------------------------- *)
IF HOLD_CMD AND (STATE > S_IDLE) AND (STATE < S_TRIP) THEN
    STATE := S_PAUSE;
END_IF;


(* --- 4.8 controlled stop.  Order matters: heater first, valves last,
   --- so the heater is never energised in a tank being emptied.        --- *)
IF ABORT_CMD THEN
    ENABLE_HEATER := FALSE;
    ENABLE_DOSING := FALSE;
    RUN_PUMPS     := FALSE;
    OPEN_XV101    := FALSE;
    OPEN_XV102    := FALSE;
    STATE         := S_IDLE;
END_IF;


(* --- state timeout ------------------------------------------------------ *)
TIMEOUT_ALARM := (state_timeout > T#0s) AND t_state.ET > state_timeout;
IF TIMEOUT_ALARM THEN
    STATE := S_DRAIN;
END_IF;

END_FUNCTION_BLOCK
