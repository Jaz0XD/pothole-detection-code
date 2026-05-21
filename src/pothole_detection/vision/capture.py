from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import cv2
import numpy as np


@dataclass
class HttpJpegCapture:
    url: str
    timeout_s: float = 2.5

    def __post_init__(self) -> None:
        self._opened = True

    def isOpened(self) -> bool:  # noqa: N802
        return self._opened

    def read(self):  # OpenCV-like interface
        if not self._opened:
            return False, None
        try:
            req = Request(self.url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = resp.read()
            frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                return False, None
            return True, frame
        except Exception:
            return False, None

    def release(self) -> None:
        self._opened = False


@dataclass
class HttpMjpegCapture:
    url: str
    timeout_s: float = 5.0
    chunk_size: int = 4096

    def __post_init__(self) -> None:
        self._opened = True
        self._resp = None
        self._buffer = bytearray()
        self._connect()

    def _connect(self) -> None:
        req = Request(self.url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
        try:
            self._resp = urlopen(req, timeout=self.timeout_s)
        except HTTPError as err:
            raise RuntimeError(f"ESP32-CAM stream HTTP error {err.code} for {self.url}") from err
        except URLError as err:
            reason = getattr(err, "reason", err)
            raise RuntimeError(
                f"Unable to connect to ESP32-CAM stream: {self.url}. "
                f"Reason: {reason}. Check ESP32 IP, endpoint (/stream), and Wi-Fi network."
            ) from err

    def isOpened(self) -> bool:  # noqa: N802
        return self._opened

    def _read_next_frame(self):
        # Many ESP32 streams are multipart MJPEG; extracting JPEG SOI/EOI works
        # even if headers/boundaries vary.
        while self._opened:
            start = self._buffer.find(b"\xff\xd8")
            if start != -1:
                end = self._buffer.find(b"\xff\xd9", start + 2)
                if end != -1:
                    jpg = bytes(self._buffer[start : end + 2])
                    del self._buffer[: end + 2]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        return True, frame
            chunk = self._resp.read(self.chunk_size)
            if not chunk:
                return False, None
            self._buffer.extend(chunk)
        return False, None

    def read(self):  # OpenCV-like interface
        if not self._opened:
            return False, None
        try:
            if self._resp is None:
                self._connect()
            return self._read_next_frame()
        except Exception:
            try:
                if self._resp:
                    self._resp.close()
            except Exception:
                pass
            self._resp = None
            self._buffer.clear()
            return False, None

    def release(self) -> None:
        self._opened = False
        if self._resp is not None:
            try:
                self._resp.close()
            except Exception:
                pass
            self._resp = None


def _is_snapshot_url(source: str) -> bool:
    lower = source.lower()
    return lower.startswith("http://") and (lower.endswith(".jpg") or "/cam-" in lower)


def _is_stream_url(source: str) -> bool:
    lower = source.lower()
    return lower.startswith("http://") and ("/stream" in lower or "mjpeg" in lower)


def open_video_source(source: str):
    if _is_snapshot_url(source):
        cap = HttpJpegCapture(source)
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError(f"Unable to fetch ESP32-CAM JPEG source: {source}")
        return cap
    if _is_stream_url(source):
        cap = HttpMjpegCapture(source)
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError(f"Unable to open MJPEG stream source: {source}")
        return cap

    parsed = int(source) if source.isdigit() else source
    cap = cv2.VideoCapture(parsed)
    if not cap.isOpened():
        if source == "0":
            raise RuntimeError(
                "Unable to open video source: 0. No local webcam detected. "
                "For ESP32-CAM use --source http://<ESP32_IP>/cam-hi.jpg"
            )
        raise RuntimeError(f"Unable to open video source: {source}")
    return cap
