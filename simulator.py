#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import socket
import threading
import time
from dataclasses import dataclass, field

from pyModbusTCP.server import DataBank, ModbusServer

REG_ALL_TEST = 0
REG_CLEAR_ALL = 1
REG_SINGLE_TEST_START = 2
REG_SINGLE_TEST_END = 9
REGISTER_COUNT = 10

VALUE_IDLE = 0
VALUE_REQUEST = 1
VALUE_RUNNING = 2
VALUE_SUCCESS = 3
VALUE_ERROR = 0xFFFF


@dataclass
class SimulatorState:
    output_count: int = 8
    test_step_delay: float = 0.5
    outputs: list[bool] = field(default_factory=lambda: [False] * 8)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def clear_outputs(self) -> None:
        with self.lock:
            self.outputs = [False] * self.output_count


class RS8Simulator:
    def __init__(self, test_step_delay: float) -> None:
        self.state = SimulatorState(test_step_delay=test_step_delay)
        self._lock = threading.Lock()
        DataBank.set_words(0, [0] * REGISTER_COUNT)

    def process_write(self, address: int, values: list[int]) -> None:
        logging.info("MODBUS WRITE | hr[%d..%d] <- %s", address, address + len(values) - 1, values)
        for offset, value in enumerate(values):
            reg = address + offset
            if value != VALUE_REQUEST:
                continue
            if reg == REG_ALL_TEST:
                logging.info("TRIGGER: REG_ALL_TEST")
                threading.Thread(target=self._run_all_test, daemon=True).start()
            elif reg == REG_CLEAR_ALL:
                logging.info("TRIGGER: REG_CLEAR_ALL")
                self._clear_all()
            elif REG_SINGLE_TEST_START <= reg <= REG_SINGLE_TEST_END:
                idx = reg - REG_SINGLE_TEST_START
                logging.info("TRIGGER: REG_RS%d_TEST", idx + 1)
                threading.Thread(target=self._run_single_test, args=(idx,), daemon=True).start()

    def _clear_all(self) -> None:
        with self._lock:
            DataBank.set_words(0, [0] * REGISTER_COUNT)
            self.state.clear_outputs()
        logging.info("Tüm register/output sıfırlandı.")

    def _run_all_test(self) -> None:
        for i in range(self.state.output_count):
            with self.state.lock:
                self.state.outputs[i] = True
            logging.info("RS%d AKTIF", i + 1)
            time.sleep(self.state.test_step_delay)
            with self.state.lock:
                self.state.outputs[i] = False
            logging.info("RS%d PASIF", i + 1)
        DataBank.set_words(REG_ALL_TEST, [0])
        logging.info("ALL_TEST tamamlandı.")

    def _run_single_test(self, idx: int) -> None:
        reg = REG_SINGLE_TEST_START + idx
        try:
            DataBank.set_words(reg, [VALUE_RUNNING])
            with self.state.lock:
                self.state.outputs[idx] = True
            time.sleep(self.state.test_step_delay)
            with self.state.lock:
                self.state.outputs[idx] = False
            DataBank.set_words(reg, [VALUE_SUCCESS])
            logging.info("RS%d test BAŞARILI", idx + 1)
        except Exception:
            DataBank.set_words(reg, [VALUE_ERROR])
            logging.exception("RS%d test HATALI", idx + 1)


def resolve_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def beacon_sender(name: str, ip: str, modbus_port: int, udp_port: int, interval: float) -> None:
    msg = f"name={name};ip={ip};port={modbus_port}".encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        s.sendto(msg, ("255.255.255.255", udp_port))
        time.sleep(interval)


def write_monitor(sim: RS8Simulator, poll: float = 0.05) -> None:
    prev = DataBank.get_words(0, REGISTER_COUNT)
    while True:
        cur = DataBank.get_words(0, REGISTER_COUNT)
        if cur != prev:
            changes = []
            for i, (a, b) in enumerate(zip(prev, cur)):
                if a != b:
                    changes.append((i, b))
            for addr, val in changes:
                sim.process_write(addr, [val])
            prev = cur
        time.sleep(poll)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="RS8-SIM")
    ap.add_argument("--modbus-port", type=int, default=5020)
    ap.add_argument("--beacon-udp-port", type=int, default=37020)
    ap.add_argument("--beacon-interval", type=float, default=2.0)
    ap.add_argument("--test-step-delay", type=float, default=0.5)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    ip = resolve_local_ip()
    logging.info("Cihaz adı: %s", args.name)
    logging.info("Modbus TCP: %s:%d", ip, args.modbus_port)

    sim = RS8Simulator(test_step_delay=args.test_step_delay)
    threading.Thread(target=beacon_sender, args=(args.name, ip, args.modbus_port, args.beacon_udp_port, args.beacon_interval), daemon=True).start()
    threading.Thread(target=write_monitor, args=(sim,), daemon=True).start()

    server = ModbusServer(host="0.0.0.0", port=args.modbus_port, no_block=True)
    server.start()
    logging.info("Server listening.")
    try:
        while True:
            # read log can be sampled
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
