#!/usr/bin/env python3
"""WTS-100 plant simulator exposed as a Modbus TCP server.

Run:  python3 plant_server.py

Listens on 127.0.0.1:5020 and serves the simulated skid as Modbus registers,
the same way a real remote I/O rack would.  The controller (plc.py) connects
as a client and has no idea the plant is software.

    input registers   30001+   analog inputs, raw counts
    discrete inputs   10001+   digital inputs
    holding registers 40001+   analog outputs, raw counts
    coils             00001+   digital outputs

Analog values cross as COUNTS, not engineering units, exactly as they would
from a 4-20 mA card.  Scaling is the controller's job.
"""
import asyncio, argparse, logging
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server import StartAsyncTcpServer

from plant import Plant
import modbus_map as M

logging.getLogger("pymodbus").setLevel(logging.WARNING)

HOST, PORT = "127.0.0.1", 5020
CYCLE = 0.1                       # 100 ms, matches the plant timestep


class PlantServer:
    def __init__(self, speed=1.0):
        self.plant = Plant(dt=CYCLE)
        self.speed = speed        # >1 runs the process faster than real time
        self.store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0]*32),
            co=ModbusSequentialDataBlock(0, [0]*32),
            hr=ModbusSequentialDataBlock(0, [0]*32),
            ir=ModbusSequentialDataBlock(0, [0]*32),
        )
        self.ctx = ModbusServerContext(slaves=self.store, single=True)

    # ---------------------------------------------------------------- helpers
    def _read_coils(self):
        c = self.store.getValues(1, 0, count=len(M.DO))
        return {name: bool(c[i]) for name, i in M.DO.items()}

    def _read_holding(self):
        h = self.store.getValues(3, 0, count=len(M.AO))
        out = {}
        for name, (idx, lo, hi) in M.AO.items():
            val, _ = M.counts_to_eu(h[idx], lo, hi)
            out[name] = val
        return out

    def _write_inputs(self, readings):
        self.store.setValues(4, 0, M.encode_ai(readings))          # input regs
        di = [0]*len(M.DI)
        for name, i in M.DI.items():
            di[i] = int(bool(readings[name]))
        self.store.setValues(2, 0, di)                             # discrete in

    # ------------------------------------------------------------------ loop
    async def run(self):
        p = self.plant
        while True:
            coils = self._read_coils()
            ao    = self._read_holding()

            # commands from the controller
            p.cmd_pump_a   = coils["MTR_101A"]
            p.cmd_pump_b   = coils["MTR_101B"]
            p.cmd_xv101    = coils["XV_101"]
            p.cmd_xv102    = coils["XV_102"]
            p.cmd_htr_en   = coils["HTR_EN"]
            p.cmd_fcv_pct  = ao["FCV_101"]
            p.cmd_htr_pct  = ao["HTR_101"]
            p.cmd_dose_pct = ao["P_103"]
            p.cmd_p102_pct = ao["P_102"]

            readings = p.step()
            self._write_inputs(readings)

            await asyncio.sleep(CYCLE / self.speed)


async def main(speed):
    srv = PlantServer(speed=speed)
    print(f"WTS-100 plant simulator on {HOST}:{PORT}   speed x{speed}")
    print("  input regs  30001+  analog in    discrete in 10001+  switches")
    print("  holding     40001+  analog out   coils       00001+  motors and valves")
    asyncio.create_task(srv.run())
    await StartAsyncTcpServer(context=srv.ctx, address=(HOST, PORT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=10.0,
                    help="simulation speed multiplier, default 60 so a 45 min "
                         "heat up takes 45 s")
    a = ap.parse_args()
    try:
        asyncio.run(main(a.speed))
    except KeyboardInterrupt:
        print("\nstopped")
