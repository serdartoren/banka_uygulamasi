#!/usr/bin/env python3
"""RS çıkış test sistemi için Modbus TCP simülatörü."""

from __future__ import annotations

import argparse
import logging
import socket
import threading
import time
from dataclasses import dataclass, field

from pymodbus.datastore import ModbusDeviceContext, ModbusServerContext, ModbusSparseDataBlock
from pymodbus.server import StartTcpServer


@dataclass
class SimulatorState:
    """Simülasyonun iç durumunu tutar."""

    output_count: int = 8
    test_step_delay: float = 0.5
    outputs: list[bool] = field(default_factory=lambda: [False] * 8)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def clear(self) -> None:
        with self.lock:
            self.outputs = [False] * self.output_count
            logging.info("Tüm çıkış durumları temizlendi.")

    def set_output(self, index: int, value: bool) -> None:
        with self.lock:
            self.outputs[index] = value
            logging.info("RS%d durumu: %s", index + 1, "AKTIF" if value else "PASIF")

    def run_all_output_test(self) -> None:
        logging.info("8 çıkışın tamamı için test başlatıldı.")
        for idx in range(self.output_count):
            self.set_output(idx, True)
            time.sleep(self.test_step_delay)
            self.set_output(idx, False)
        logging.info("8 çıkış toplu testi tamamlandı.")

    def run_single_output_test(self, index: int) -> None:
        logging.info("RS%d için tekil test başlatıldı.", index + 1)
        self.set_output(index, True)
        time.sleep(self.test_step_delay)
        self.set_output(index, False)
        logging.info("RS%d tekil testi tamamlandı.", index + 1)


class SimulatorDataBlock(ModbusSparseDataBlock):
    """Register yazımlarını yakalayan Modbus data block."""

    VALUE_IDLE = 0
    VALUE_REQUEST = 1
    VALUE_RUNNING = 2
    VALUE_SUCCESS = 3
    VALUE_ERROR = 0xFFFF  # Modbus'ta signed -1 karşılığı

    # Modbus istemcilerde 0..9 gibi görünen ofsetler
    REG_ALL_TEST = 0
    REG_CLEAR_ALL = 1
    REG_SINGLE_TEST_START = 2
    REG_SINGLE_TEST_END = 9

    def __init__(self, state: SimulatorState) -> None:
        # 0..9 holding register ofsetlerini doğrudan kabul eder
        super().__init__({i: 0 for i in range(10)})
        self.state = state

    def getValues(self, address, count=1):  # noqa: N802 - pymodbus API
        values = super().getValues(address, count=count)
        start_reg = address
        end_reg = start_reg + count - 1
        logging.info("MODBUS READ  | hr[%d..%d] -> %s", start_reg, end_reg, values)
        return values

    def setValues(self, address, values):  # noqa: N802 - pymodbus API
        # pymodbus datastore iç adreslemeyi çoğu sürümde 1 tabanlı verir.
        # Biz dokümantasyonda 0..9 ofset kullanıyoruz, bu yüzden normalize ediyoruz.
        super().setValues(address, values)

        logging.info("MODBUS WRITE | hr[%d..%d] <- %s", address, address + len(values) - 1, values)

        for offset, value in enumerate(values):
            reg = address + offset
            if reg == self.REG_ALL_TEST and value == self.VALUE_REQUEST:
                logging.info("TRIGGER: REG_ALL_TEST (reg=%d) isteği alındı.", reg)
                threading.Thread(target=self._run_all_test_and_reset, daemon=True).start()
            elif reg == self.REG_CLEAR_ALL and value == self.VALUE_REQUEST:
                logging.info("TRIGGER: REG_CLEAR_ALL (reg=%d) isteği alındı.", reg)
                self._clear_all_registers()
            elif self.REG_SINGLE_TEST_START <= reg <= self.REG_SINGLE_TEST_END and value == self.VALUE_REQUEST:
                index = reg - self.REG_SINGLE_TEST_START
                logging.info("TRIGGER: REG_RS%d_TEST (reg=%d) isteği alındı.", index + 1, reg)
                threading.Thread(target=self._run_single_test_with_status, args=(index,), daemon=True).start()

    def _clear_all_registers(self) -> None:
        self.state.clear()
        super().setValues(0, [0] * 10)
        logging.info("10 register sıfırlandı.")

    def _run_all_test_and_reset(self) -> None:
        self.state.run_all_output_test()
        super().setValues(self.REG_ALL_TEST, [0])

    def _run_single_test_with_status(self, index: int) -> None:
        reg_addr = self.REG_SINGLE_TEST_START + index
        try:
            super().setValues(reg_addr, [self.VALUE_RUNNING])
            self.state.run_single_output_test(index)
            super().setValues(reg_addr, [self.VALUE_SUCCESS])
        except Exception:
            logging.exception("RS%d testinde hata oluştu.", index + 1)
            super().setValues(reg_addr, [self.VALUE_ERROR])


def resolve_local_ip() -> str:
    """Yerel ağ IP adresini bulur."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


def beacon_sender(name: str, ip: str, modbus_port: int, udp_port: int, interval: float) -> None:
    """UDP broadcast beacon yayınlar."""
    message = f"name={name};ip={ip};port={modbus_port}".encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        sock.sendto(message, ("255.255.255.255", udp_port))
        logging.info("Beacon gönderildi.")
        time.sleep(interval)


def run_server(name: str, modbus_port: int, beacon_udp_port: int, beacon_interval: float, test_step_delay: float) -> None:
    ip = resolve_local_ip()
    logging.info("Cihaz adı: %s", name)
    logging.info("Modbus TCP: %s:%d", ip, modbus_port)

    state = SimulatorState(test_step_delay=test_step_delay)
    block = SimulatorDataBlock(state)
    # Sadece Holding Register (hr) alanını aktif kullanıyoruz.
    # Coils / Discrete Inputs / Input Registers tanımlı değildir.
    # zero_mode=True ile client adresleri 0-tabanlı (0..9) birebir yorumlanır.
    context = ModbusServerContext(devices=ModbusDeviceContext(hr=block, zero_mode=True), single=True)

    threading.Thread(
        target=beacon_sender,
        args=(name, ip, modbus_port, beacon_udp_port, beacon_interval),
        daemon=True,
    ).start()

    StartTcpServer(context, address=("0.0.0.0", modbus_port))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="8 RS çıkış test sistemi Modbus TCP simülatörü")
    parser.add_argument("--name", default="RS8-SIM", help="Cihaz adı")
    parser.add_argument("--modbus-port", type=int, default=5020, help="Modbus TCP portu")
    parser.add_argument("--beacon-udp-port", type=int, default=37020, help="UDP beacon portu")
    parser.add_argument("--beacon-interval", type=float, default=2.0, help="Beacon periyodu (saniye)")
    parser.add_argument("--test-step-delay", type=float, default=0.5, help="Her kanal test adımı bekleme süresi")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logging.getLogger("pymodbus").setLevel(logging.INFO)
    args = parse_args()
    run_server(
        name=args.name,
        modbus_port=args.modbus_port,
        beacon_udp_port=args.beacon_udp_port,
        beacon_interval=args.beacon_interval,
        test_step_delay=args.test_step_delay,
    )
