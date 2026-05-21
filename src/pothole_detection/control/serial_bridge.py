from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from pothole_detection.control.policy import VehicleCommand


@dataclass(slots=True)
class SerialBridge:
    port: str | None
    baudrate: int = 115200
    min_interval_ms: int = 150
    _serial: Any = field(init=False, default=None, repr=False)
    _last_sent_at: float = field(init=False, default=0.0, repr=False)
    _last_line: str = field(init=False, default="", repr=False)

    def __post_init__(self) -> None:
        if self.port:
            import serial

            self._serial = serial.Serial(self.port, self.baudrate, timeout=1)

    def send(self, command: VehicleCommand) -> None:
        line = command.to_line()
        now = time.time() * 1000.0
        if line == self._last_line and (now - self._last_sent_at) < self.min_interval_ms:
            return

        self._last_line = line
        self._last_sent_at = now

        if self._serial:
            self._serial.write((line + "\n").encode("utf-8"))
        else:
            print(f"[SERIAL-MOCK] {line}")

    def close(self) -> None:
        if self._serial:
            self._serial.close()
