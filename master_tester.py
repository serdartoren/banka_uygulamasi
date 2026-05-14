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


def _read_holding_registers(client: ModbusTcpClient, address: int, count: int, unit_id: int):
    """pymodbus sürümleri arası parametre farkını tolere eder."""
    try:
        return client.read_holding_registers(address=address, count=count, slave=unit_id)
    except TypeError:
        return client.read_holding_registers(address=address, count=count, device_id=unit_id)


def _write_register(client: ModbusTcpClient, address: int, value: int, unit_id: int):
    """pymodbus sürümleri arası parametre farkını tolere eder."""
    try:
        return client.write_register(address=address, value=value, slave=unit_id)
    except TypeError:
        return client.write_register(address=address, value=value, device_id=unit_id)


def read_registers(client: ModbusTcpClient, unit_id: int, base_address: int) -> List[int]:
    rr = _read_holding_registers(client, address=base_address, count=REGISTER_COUNT, unit_id=unit_id)
    if rr.isError():
        raise RuntimeError(f"Register okuma hatası: {rr}")
    return list(rr.registers)


def write_single(client: ModbusTcpClient, unit_id: int, address: int, value: int, base_address: int) -> None:
    wr = _write_register(client, address=address + base_address, value=value, unit_id=unit_id)
    if wr.isError():
        raise RuntimeError(f"Register yazma hatası (addr={address}, value={value}): {wr}")


def wait_rs_status(client: ModbusTcpClient, unit_id: int, rs_index: int, timeout: float, poll: float, base_address: int) -> int:
    reg = REG_RS1_TEST + rs_index
    deadline = time.time() + timeout

    saw_running = False
    while time.time() < deadline:
        vals = read_registers(client, unit_id, base_address=base_address)
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




def detect_base_address(client: ModbusTcpClient, unit_id: int) -> int:
    """Sunucunun 0- veya 1-tabanlı adresleme beklentisini tespit eder."""
    for base in (0, 1):
        rr = _read_holding_registers(client, address=base, count=REGISTER_COUNT, unit_id=unit_id)
        if not rr.isError():
            return base
    raise RuntimeError("Register okuma başarısız: hem 0-tabanlı hem 1-tabanlı denemeler hata verdi.")

def run_test(host: str, port: int, unit_id: int, timeout: float, poll: float) -> None:
    client = ModbusTcpClient(host=host, port=port)
    if not client.connect():
        raise ConnectionError(f"Bağlantı kurulamadı: {host}:{port}")

    try:
        base_address = detect_base_address(client, unit_id)
        print(f"Adresleme tabanı algılandı: {base_address}")

        print("--- Başlangıç register okuma ---")
        print(read_registers(client, unit_id, base_address=base_address))

        print("\n--- Clear All (reg1=1) ---")
        write_single(client, unit_id, REG_CLEAR_ALL, 1, base_address=base_address)
        time.sleep(0.2)
        print(read_registers(client, unit_id, base_address=base_address))

        print("\n--- RS1 tekil test (reg2=1) ---")
        write_single(client, unit_id, REG_RS1_TEST, STATUS_REQUEST, base_address=base_address)
        final = wait_rs_status(client, unit_id, rs_index=0, timeout=timeout, poll=poll, base_address=base_address)
        if final == STATUS_SUCCESS:
            print("RS1 test sonucu: BAŞARILI (3)")
        elif final == STATUS_ERROR:
            print("RS1 test sonucu: HATALI (-1 / 65535)")

        print("\n--- Tüm test (reg0=1) ---")
        write_single(client, unit_id, REG_ALL_TEST, 1, base_address=base_address)
        # Toplu testte statüler tek tek register'a yazılmadığı için kısa bekleme + okuma
        time.sleep(5)
        print(read_registers(client, unit_id, base_address=base_address))

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
