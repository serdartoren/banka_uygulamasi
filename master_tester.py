#!/usr/bin/env python3
"""RS8 Modbus simülatörünü test eden master (client) uygulaması."""

from __future__ import annotations

import argparse
import time
from typing import List

from pymodbus.client import ModbusTcpClient

REG_ALL_TEST = 0
REG_CLEAR_ALL = 1
REG_RS1_TEST = 2
REGISTER_COUNT = 10

STATUS_IDLE = 0
STATUS_REQUEST = 1
STATUS_RUNNING = 2
STATUS_SUCCESS = 3
STATUS_ERROR = 0xFFFF


def read_registers(client: ModbusTcpClient, unit_id: int) -> List[int]:
    rr = client.read_holding_registers(address=0, count=REGISTER_COUNT, slave=unit_id)
    if rr.isError():
        raise RuntimeError(f"Register okuma hatası: {rr}")
    return list(rr.registers)


def write_single(client: ModbusTcpClient, unit_id: int, address: int, value: int) -> None:
    wr = client.write_register(address=address, value=value, slave=unit_id)
    if wr.isError():
        raise RuntimeError(f"Register yazma hatası (addr={address}, value={value}): {wr}")


def wait_rs_status(client: ModbusTcpClient, unit_id: int, rs_index: int, timeout: float, poll: float) -> int:
    reg = REG_RS1_TEST + rs_index
    deadline = time.time() + timeout

    saw_running = False
    while time.time() < deadline:
        vals = read_registers(client, unit_id)
        status = vals[reg]
        print(f"RS{rs_index + 1} status={status}")

        if status == STATUS_RUNNING:
            saw_running = True
        if status in (STATUS_SUCCESS, STATUS_ERROR):
            if not saw_running:
                print("Uyarı: RUNNING(2) gözlenmeden terminal duruma ulaşıldı.")
            return status

        time.sleep(poll)

    raise TimeoutError(f"RS{rs_index + 1} durum bekleme timeout")


def run_test(host: str, port: int, unit_id: int, timeout: float, poll: float) -> None:
    client = ModbusTcpClient(host=host, port=port)
    if not client.connect():
        raise ConnectionError(f"Bağlantı kurulamadı: {host}:{port}")

    try:
        print("--- Başlangıç register okuma ---")
        print(read_registers(client, unit_id))

        print("\n--- Clear All (reg1=1) ---")
        write_single(client, unit_id, REG_CLEAR_ALL, 1)
        time.sleep(0.2)
        print(read_registers(client, unit_id))

        print("\n--- RS1 tekil test (reg2=1) ---")
        write_single(client, unit_id, REG_RS1_TEST, STATUS_REQUEST)
        final = wait_rs_status(client, unit_id, rs_index=0, timeout=timeout, poll=poll)
        if final == STATUS_SUCCESS:
            print("RS1 test sonucu: BAŞARILI (3)")
        elif final == STATUS_ERROR:
            print("RS1 test sonucu: HATALI (-1 / 65535)")

        print("\n--- Tüm test (reg0=1) ---")
        write_single(client, unit_id, REG_ALL_TEST, 1)
        # Toplu testte statüler tek tek register'a yazılmadığı için kısa bekleme + okuma
        time.sleep(5)
        print(read_registers(client, unit_id))

        print("\nMaster test tamamlandı.")

    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RS8 Modbus simülatörü için master test istemcisi")
    p.add_argument("--host", default="127.0.0.1", help="Simülatör IP adresi")
    p.add_argument("--port", type=int, default=5020, help="Simülatör Modbus TCP portu")
    p.add_argument("--unit-id", type=int, default=1, help="Modbus Unit ID / Slave ID")
    p.add_argument("--timeout", type=float, default=10.0, help="Durum bekleme timeout (sn)")
    p.add_argument("--poll", type=float, default=0.25, help="Durum okuma periyodu (sn)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_test(args.host, args.port, args.unit_id, args.timeout, args.poll)
