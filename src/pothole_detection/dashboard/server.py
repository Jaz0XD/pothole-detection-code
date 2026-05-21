#Dashboard Frontend

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from pothole_detection.config.settings import DashboardConfig


HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pothole Dashboard</title>
  <style>
    :root { color-scheme: light; --bg:#f3f0e8; --card:#fffdf8; --ink:#1b1f1e; --muted:#59615d; --ok:#2d7f5e; --warn:#c78b2d; --bad:#b42318; }
    body { margin:0; font-family: Georgia, "Times New Roman", serif; background: radial-gradient(circle at top, #fffaf0, var(--bg)); color:var(--ink); }
    .wrap { max-width: 1100px; margin: 0 auto; padding: 24px; }
    h1 { margin: 0 0 16px; font-size: 2rem; letter-spacing: .03em; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
    .card { background: var(--card); border: 1px solid #ddd2bf; border-radius: 18px; padding: 18px; box-shadow: 0 6px 24px rgba(40,30,20,.07); }
    .label { font-size: .85rem; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }
    .value { font-size: 2rem; margin-top: 8px; }
    .small { font-size: 1rem; color: var(--muted); margin-top: 6px; }
    .severity-none { color: var(--ok); }
    .severity-minor { color: var(--ok); }
    .severity-moderate { color: var(--warn); }
    .severity-severe { color: var(--bad); }
    img { max-width: 100%; border-radius: 18px; border: 1px solid #ddd2bf; }
    .row { display:grid; grid-template-columns: 1.3fr .7fr; gap:16px; margin-top:16px; }
    .stack { display:grid; gap:12px; margin-top:12px; }
    .input { width: 100%; box-sizing: border-box; border: 1px solid #cfc3ae; border-radius: 12px; padding: 10px 12px; font-size: 1rem; font-family: "Courier New", monospace; background: #fffdf9; }
    .btn { border: 1px solid #a99571; background: #f8edd4; color: #3d311f; border-radius: 12px; padding: 8px 12px; font-size: .95rem; cursor: pointer; }
    .mono { font-family: "Courier New", monospace; font-size: .9rem; color: #3a3a3a; word-break: break-all; }
    @media (max-width: 900px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Pothole Detection Telemetry</h1>
    <div class="grid">
      <div class="card"><div class="label">Detection</div><div class="value" id="detection-enabled">-</div><div class="small">Inference pipeline status</div></div>
      <div class="card"><div class="label">Vehicle Speed</div><div class="value" id="speed">-</div><div class="small">Commanded speed percentage</div></div>
      <div class="card"><div class="label">Pothole Distance</div><div class="value" id="distance">-</div><div class="small">Estimated forward range</div></div>
      <div class="card"><div class="label">Severity</div><div class="value" id="severity">-</div><div class="small" id="command">-</div></div>
      <div class="card"><div class="label">Geometry</div><div class="small" id="geometry">-</div></div>
      <div class="card"><div class="label">Online Learning</div><div class="small" id="learning">-</div></div>
    </div>
    <div class="row">
      <div class="card">
        <div class="label">Live Preview</div>
        <div class="small">Preview can stay hidden while telemetry remains active.</div>
        <img id="preview" alt="preview">
      </div>
      <div class="card">
        <div class="label">Runtime</div>
        <div class="small" id="runtime">Waiting for telemetry...</div>
        <div class="stack">
          <div class="label">ESP32-CAM Setup</div>
          <input id="esp32-ip" class="input" placeholder="192.168.1.100 or http://192.168.1.100">
          <button id="save-ip" class="btn">Save ESP32 IP</button>
          <div class="small">Use this source in detection process:</div>
          <div id="source-url" class="mono">http://ESP32_IP/cam-hi.jpg</div>
          <div class="small">Start command:</div>
          <div id="run-cmd" class="mono">python app.py --source http://ESP32_IP/cam-hi.jpg --model-path runs/detect/train/weights/best.pt</div>
        </div>
      </div>
    </div>
  </div>
  <script>
    function normalizeBase(raw) {
      const trimmed = (raw || '').trim();
      if (!trimmed) return '';
      if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed.replace(/\\/+$/, '');
      return `http://${trimmed.replace(/\\/+$/, '')}`;
    }
    function applyEsp32Ui() {
      const base = normalizeBase(localStorage.getItem('esp32_cam_ip') || '');
      const source = base ? `${base}/cam-hi.jpg` : 'http://ESP32_IP/cam-hi.jpg';
      document.getElementById('source-url').textContent = source;
      document.getElementById('run-cmd').textContent =
        `python app.py --source ${source} --model-path runs/detect/train/weights/best.pt`;
    }
    function initEsp32Ui() {
      const input = document.getElementById('esp32-ip');
      const saved = localStorage.getItem('esp32_cam_ip') || '';
      input.value = saved;
      applyEsp32Ui();
      document.getElementById('save-ip').addEventListener('click', () => {
        localStorage.setItem('esp32_cam_ip', input.value.trim());
        applyEsp32Ui();
      });
    }

    async function refresh() {
      const res = await fetch('/state');
      const data = await res.json();
      document.getElementById('detection-enabled').textContent = data.detection_enabled ? 'Enabled' : 'Disabled';
      document.getElementById('speed').textContent = `${data.vehicle_speed_pct}%`;
      document.getElementById('distance').textContent = data.top_detection.distance_m == null ? 'No pothole' : `${data.top_detection.distance_m.toFixed(2)} m`;
      const sev = document.getElementById('severity');
      sev.textContent = data.top_detection.severity;
      sev.className = `value severity-${data.top_detection.severity}`;
      document.getElementById('command').textContent = data.command;
      document.getElementById('geometry').textContent =
        `width ${formatNum(data.top_detection.width_m)} m | length ${formatNum(data.top_detection.length_m)} m | depth ${formatNum(data.top_detection.depth_m)} m`;
      document.getElementById('learning').textContent =
        `${data.online_samples} captured samples | ${data.retrain_runs} retrain runs`;
      document.getElementById('runtime').textContent =
        `FPS ${data.fps.toFixed(1)} | detections ${data.detections_seen} | updated ${data.timestamp}`;
      const preview = document.getElementById('preview');
      if (data.preview_path) {
        preview.style.display = 'block';
        preview.src = `/frame?ts=${Date.now()}`;
      } else {
        preview.style.display = 'none';
      }
    }
    function formatNum(value) {
      return value == null ? '-' : value.toFixed(2);
    }
    initEsp32Ui();
    refresh();
    setInterval(refresh, 1000);
  </script>
</body>
</html>
"""


class DashboardServer:
    def __init__(self, config: DashboardConfig) -> None:
        self.config = config
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.config.enabled:
            return

        state_path = Path(self.config.state_path)
        snapshot_path = Path(self.config.snapshot_path)

        class Handler(BaseHTTPRequestHandler):
            def _send(self, code: int, content_type: str, body: bytes) -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                if self.path.startswith("/state"):
                    if state_path.exists():
                        self._send(200, "application/json", state_path.read_bytes())
                    else:
                        self._send(200, "application/json", json.dumps({}).encode("utf-8"))
                    return
                if self.path.startswith("/frame"):
                    if snapshot_path.exists():
                        self._send(200, "image/jpeg", snapshot_path.read_bytes())
                    else:
                        self._send(404, "text/plain", b"no frame")
                    return
                self._send(200, "text/html; charset=utf-8", HTML.encode("utf-8"))

            def log_message(self, format: str, *args) -> None:
                return

        self._server = ThreadingHTTPServer((self.config.host, self.config.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"[DASHBOARD] http://{self.config.host}:{self.config.port}")

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
