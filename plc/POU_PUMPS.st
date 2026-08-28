(*
    WTS-100  POU_PUMPS
    Duty and standby raw water pumps.  IEC 61131-3 Structured Text.

    Same logic as the ladder drawing drawings/ladder_pumps.svg.

    Logic verified by test_ladder.py, 10 cases.
*)

FUNCTION_BLOCK POU_PUMPS

VAR_INPUT
    HS_02_START     : BOOL;   (* start pushbutton, momentary NO   *)
    HS_03_STOP_OK   : BOOL;   (* stop pushbutton, wired NC        *)
    PERM_RAW_PUMPS  : BOOL;   (* from POU_SAFETY                  *)
    XS_101A         : BOOL;   (* pump A run feedback              *)
    XS_101B         : BOOL;   (* pump B run feedback              *)
    BATCH_DONE      : BOOL;   (* one shot at end of a batch       *)
END_VAR

VAR_OUTPUT
    MTR_101A            : BOOL;
    MTR_101B            : BOOL;
    RUN_REQ             : BOOL;
    FAULT_A             : BOOL;
    FAULT_B             : BOOL;
    BOTH_PUMPS_FAILED   : BOOL;
    DUTY_IS_A           : BOOL := TRUE;
END_VAR

VAR
    tA          : TON;
    tB          : TON;
    batch_prev  : BOOL;
END_VAR


(* --- RUNG 1  start and stop with seal in.
   --- The seal in parallels the START contact ONLY.  Stop and the safety
   --- permission stay in series after it, so both can always break the rung.
   --- Putting them inside the seal in would mean the stop button does not
   --- stop the pumps once they are running.                              --- *)
RUN_REQ := (HS_02_START OR RUN_REQ) AND HS_03_STOP_OK AND PERM_RAW_PUMPS;


(* --- duty alternation.  Swap on each completed batch so running hours
   --- stay even between the two pumps.                                   --- *)
IF BATCH_DONE AND NOT batch_prev THEN
    DUTY_IS_A := NOT DUTY_IS_A;
END_IF;
batch_prev := BATCH_DONE;


(* --- RUNG 2  duty pump A                                               --- *)
MTR_101A := RUN_REQ AND DUTY_IS_A AND NOT FAULT_A;

(* --- RUNG 3  standby pump B.  Runs when B is duty, or when A has failed --- *)
MTR_101B := RUN_REQ AND NOT FAULT_B AND ((NOT DUTY_IS_A) OR FAULT_A);


(* --- RUNG 4 and 5  fault detection.
   --- Commanded on but no run feedback within 3 s means the motor did not
   --- actually start: tripped overload, failed contactor, blown fuse.    --- *)
tA(IN := MTR_101A AND NOT XS_101A, PT := T#3s);
tB(IN := MTR_101B AND NOT XS_101B, PT := T#3s);

IF tA.Q THEN FAULT_A := TRUE; END_IF;
IF tB.Q THEN FAULT_B := TRUE; END_IF;


(* --- RUNG 6  both pumps failed.  Interlock I6, trips the plant.        --- *)
BOTH_PUMPS_FAILED := FAULT_A AND FAULT_B;

END_FUNCTION_BLOCK
