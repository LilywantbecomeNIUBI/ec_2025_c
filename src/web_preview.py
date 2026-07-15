"""无额外依赖的浏览器实时预览、MJPEG 和调试快照服务。"""

import copy
import json
import logging
import os
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import cv2

from config import get_web_config
from src.artifacts import save_detection_artifacts
from src.camera import CameraReader
from src.detection import analyze_frame
from src.result import create_result
from src.visualization import draw_detection_overlay


LOGGER = logging.getLogger(__name__)
MJPEG_BOUNDARY = "ec2025frame"


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EC_2025_C 实时视觉调试</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #071018;
      --panel: #101c27;
      --panel-2: #162531;
      --line: #29404e;
      --text: #ecf6f8;
      --muted: #91a8b3;
      --cyan: #42d9d0;
      --green: #5ce083;
      --amber: #ffbf5b;
      --red: #ff6b6b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(circle at 15% 0%, #123043 0, var(--bg) 42%);
      color: var(--text);
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 20px clamp(18px, 4vw, 48px);
      border-bottom: 1px solid var(--line);
      background: rgba(7, 16, 24, .82);
    }
    h1 { margin: 0; font-size: clamp(20px, 3vw, 30px); letter-spacing: .03em; }
    .subtitle { color: var(--muted); margin-top: 5px; font-size: 13px; }
    .live-pill {
      padding: 7px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--amber);
      background: var(--panel);
      font-size: 13px;
    }
    .live-pill.online { color: var(--green); border-color: #2d6842; }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1.7fr) minmax(280px, .8fr);
      gap: 20px;
      padding: 22px clamp(18px, 4vw, 48px) 34px;
    }
    .card {
      background: linear-gradient(145deg, rgba(22,37,49,.96), rgba(13,26,36,.96));
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 18px 55px rgba(0,0,0,.22);
      overflow: hidden;
    }
    .card-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 13px 16px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 13px;
    }
    .stream-wrap {
      aspect-ratio: 4 / 3;
      display: grid;
      place-items: center;
      background: #020609;
      position: relative;
    }
    #stream { width: 100%; height: 100%; object-fit: contain; display: block; }
    .nano-badge {
      position: absolute;
      right: 12px;
      bottom: 12px;
      padding: 5px 8px;
      border-radius: 6px;
      background: rgba(0,0,0,.68);
      color: var(--cyan);
      font-size: 11px;
      pointer-events: none;
    }
    aside { display: flex; flex-direction: column; gap: 16px; }
    .status-block { padding: 16px; }
    .primary-status {
      font-size: 22px;
      font-weight: 700;
      margin: 2px 0 4px;
      color: var(--amber);
      overflow-wrap: anywhere;
    }
    .primary-status.ok { color: var(--green); }
    .primary-status.error { color: var(--red); }
    .message { color: var(--muted); min-height: 36px; font-size: 13px; line-height: 1.45; }
    .metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .metric { padding: 11px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel-2); }
    .metric span { display: block; color: var(--muted); font-size: 11px; margin-bottom: 5px; }
    .metric strong { font-size: 17px; font-variant-numeric: tabular-nums; }
    button {
      width: 100%;
      border: 0;
      border-radius: 10px;
      padding: 12px 14px;
      font: inherit;
      font-weight: 700;
      color: #031313;
      background: linear-gradient(135deg, var(--cyan), #74e897);
      cursor: pointer;
    }
    button:disabled { opacity: .45; cursor: wait; }
    .snapshot-note { margin-top: 10px; min-height: 34px; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
    .notice { padding: 14px 16px; color: var(--muted); font-size: 12px; line-height: 1.55; }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      aside { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 620px) {
      header { align-items: flex-start; }
      aside { display: flex; }
      .metrics { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>EC_2025_C · 实时视觉调试</h1>
      <div class="subtitle">单目视觉目标物测量装置 / Nano 本地计算</div>
    </div>
    <div id="connection" class="live-pill">正在连接</div>
  </header>
  <main>
    <section class="card">
      <div class="card-title"><span>实时标注画面</span><span id="resolution">--</span></div>
      <div class="stream-wrap">
        <img id="stream" src="/stream.mjpg" alt="Nano 实时标注视频">
        <div class="nano-badge">COMPUTED ON JETSON NANO</div>
      </div>
    </section>
    <aside>
      <section class="card status-block">
        <div class="card-title" style="padding:0 0 12px;border:0">当前检测</div>
        <div id="status" class="primary-status">等待首帧</div>
        <div id="message" class="message">摄像头启动和预热期间请稍候。</div>
        <div class="metrics">
          <div class="metric"><span>形状</span><strong id="shape">--</strong></div>
          <div class="metric"><span>置信度</span><strong id="confidence">--</strong></div>
          <div class="metric"><span>dx / px</span><strong id="dx">--</strong></div>
          <div class="metric"><span>dy / px</span><strong id="dy">--</strong></div>
          <div class="metric"><span>处理耗时</span><strong id="latency">--</strong></div>
          <div class="metric"><span>预览 FPS</span><strong id="fps">--</strong></div>
        </div>
      </section>
      <section class="card status-block">
        <button id="snapshot" type="button">保存当前完整调试快照</button>
        <div id="snapshot-note" class="snapshot-note">只在点击时写入 outputs/，不会连续保存视频。</div>
      </section>
      <section class="card notice">
        浏览器仅显示 Nano 的计算结果，不参与视觉处理。当前阶段尚未实现距离 D、实际尺寸 x 和多帧稳定测量。
      </section>
    </aside>
  </main>
  <script>
    const byId = (id) => document.getElementById(id);
    const fmt = (value, digits = 1) => value == null ? "--" : Number(value).toFixed(digits);
    async function updateStatus() {
      try {
        const response = await fetch("/api/status", {cache: "no-store"});
        if (!response.ok) throw new Error("HTTP " + response.status);
        const data = await response.json();
        const result = data.result || {};
        byId("connection").textContent = data.running ? "LIVE · Nano 在线" : "服务已停止";
        byId("connection").classList.toggle("online", !!data.running);
        byId("status").textContent = result.status || (data.error ? "camera_error" : "等待首帧");
        byId("status").className = "primary-status " + (result.ok ? "ok" : (data.error ? "error" : ""));
        byId("message").textContent = data.error || result.message || "目标检测正常";
        byId("shape").textContent = result.shape || "--";
        byId("confidence").textContent = fmt(result.shape_confidence, 2);
        byId("dx").textContent = fmt(result.dx_px, 1);
        byId("dy").textContent = fmt(result.dy_px, 1);
        byId("latency").textContent = fmt(data.processing_ms, 1) + (data.processing_ms == null ? "" : " ms");
        byId("fps").textContent = fmt(data.preview_fps, 1);
        const camera = data.camera || {};
        byId("resolution").textContent = camera.width ? `${Math.round(camera.width)}×${Math.round(camera.height)} @ ${fmt(camera.fps, 1)} FPS` : "--";
        if (data.last_snapshot) byId("snapshot-note").textContent = "最近保存：" + data.last_snapshot;
      } catch (error) {
        byId("connection").textContent = "状态连接失败";
        byId("connection").classList.remove("online");
        byId("message").textContent = error.message;
      }
    }
    byId("snapshot").addEventListener("click", async () => {
      const button = byId("snapshot");
      button.disabled = true;
      byId("snapshot-note").textContent = "正在保存当前帧及全部中间图…";
      try {
        const response = await fetch("/api/snapshot", {method: "POST"});
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || "保存失败");
        byId("snapshot-note").textContent = "已保存：" + data.path;
      } catch (error) {
        byId("snapshot-note").textContent = "保存失败：" + error.message;
      } finally {
        button.disabled = false;
      }
    });
    updateStatus();
    setInterval(updateStatus, 500);
  </script>
</body>
</html>
"""


class SnapshotUnavailable(RuntimeError):
    """当前还没有可以保存的检测帧。"""


class PreviewState(object):
    """在采集线程和多个 HTTP 客户端之间共享唯一最新帧。"""

    def __init__(self):
        self._condition = threading.Condition()
        self._sequence = 0
        self._jpeg = None
        self._result = create_result(
            ok=False, status="starting", message="Waiting for first frame")
        self._artifacts = None
        self._camera_settings = {}
        self._running = False
        self._error = ""
        self._processing_ms = None
        self._preview_fps = 0.0
        self._last_snapshot = ""
        self._clients = 0

    def mark_started(self, camera_settings):
        with self._condition:
            self._camera_settings = dict(camera_settings or {})
            self._running = True
            self._error = ""
            self._condition.notify_all()

    def publish(self, jpeg, result, artifacts, processing_ms, preview_fps):
        with self._condition:
            self._sequence += 1
            self._jpeg = jpeg
            self._result = result
            self._artifacts = artifacts
            self._processing_ms = float(processing_ms)
            self._preview_fps = float(preview_fps)
            self._error = ""
            self._condition.notify_all()

    def set_error(self, message, result=None):
        with self._condition:
            self._error = str(message)
            if result is not None:
                self._result = result
            self._condition.notify_all()

    def mark_stopped(self):
        with self._condition:
            self._running = False
            self._condition.notify_all()

    def wait_for_jpeg(self, after_sequence, timeout_s):
        with self._condition:
            if self._sequence <= after_sequence and self._running:
                self._condition.wait(timeout_s)
            return self._sequence, self._jpeg, self._running

    def status_dict(self):
        with self._condition:
            return {
                "running": self._running,
                "sequence": self._sequence,
                "camera": dict(self._camera_settings),
                "processing_ms": self._processing_ms,
                "preview_fps": self._preview_fps,
                "error": self._error,
                "clients": self._clients,
                "last_snapshot": self._last_snapshot,
                "result": copy.deepcopy(self._result),
                "server_time": time.time(),
            }

    def snapshot_payload(self):
        with self._condition:
            if self._artifacts is None or self._sequence <= 0:
                return None
            return (
                self._sequence,
                copy.deepcopy(self._result),
                dict(self._artifacts),
            )

    def set_last_snapshot(self, path):
        with self._condition:
            self._last_snapshot = str(path)

    def change_clients(self, delta):
        with self._condition:
            self._clients = max(0, self._clients + int(delta))


class PreviewService(object):
    """持续采集、检测、JPEG 编码并只发布最新结果。"""

    def __init__(self, camera, web_config=None, analyzer=None, clock_fn=None):
        self.camera = camera
        self.web_config = get_web_config(web_config)
        self.analyzer = analyzer or analyze_frame
        self.clock = clock_fn or time.time
        self.state = PreviewState()
        self._stop_event = threading.Event()
        self._thread = None
        self._snapshot_lock = threading.Lock()

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop_event.clear()
        try:
            settings = self.camera.open()
            self.camera.warmup()
        except Exception:
            self.camera.release()
            raise
        self.state.mark_started(settings)
        self._thread = threading.Thread(
            target=self._run_loop, name="vision-preview", daemon=True)
        self._thread.start()

    def _run_loop(self):
        period_s = 1.0 / float(self.web_config["preview_fps"])
        previous_publish_time = None
        smoothed_fps = 0.0
        while not self._stop_event.is_set():
            cycle_start = self.clock()
            ok, frame, timestamp = self.camera.read()
            if not ok:
                message = self.camera.last_error or "Camera read failed"
                error_result = create_result(
                    ok=False, status="camera_error", message=message,
                    timestamp=timestamp)
                self.state.set_error(message, error_result)
                self._stop_event.wait(min(0.05, period_s))
                continue

            processing_start = self.clock()
            try:
                result, artifacts = self.analyzer(frame, timestamp)
            except Exception as exc:
                LOGGER.exception("Frame analysis failed")
                result = create_result(
                    ok=False,
                    status="processing_error",
                    message="Frame analysis failed: {}".format(exc),
                    timestamp=timestamp)
                artifacts = {
                    "original": frame.copy(),
                    "final_overlay": draw_detection_overlay(frame, result),
                }
            overlay = artifacts.get("final_overlay", frame)
            encode_parameters = [
                int(cv2.IMWRITE_JPEG_QUALITY),
                int(self.web_config["jpeg_quality"]),
            ]
            try:
                encoded_ok, encoded = cv2.imencode(
                    ".jpg", overlay, encode_parameters)
            except cv2.error as exc:
                self.state.set_error(
                    "Preview JPEG encoding failed: {}".format(exc), result)
                self._stop_event.wait(min(0.05, period_s))
                continue
            if not encoded_ok:
                self.state.set_error("Cannot encode preview JPEG", result)
                self._stop_event.wait(min(0.05, period_s))
                continue

            publish_time = self.clock()
            if previous_publish_time is not None:
                interval = publish_time - previous_publish_time
                if interval > 1e-6:
                    instant_fps = 1.0 / interval
                    if smoothed_fps <= 0:
                        smoothed_fps = instant_fps
                    else:
                        smoothed_fps = 0.8 * smoothed_fps + 0.2 * instant_fps
            previous_publish_time = publish_time
            processing_ms = (publish_time - processing_start) * 1000.0
            self.state.publish(
                encoded.tobytes(), result, artifacts,
                processing_ms, smoothed_fps)

            remaining = period_s - (self.clock() - cycle_start)
            if remaining > 0:
                self._stop_event.wait(remaining)
        self.state.mark_stopped()

    def stop(self):
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3.0)
        self._thread = None
        self.camera.release()
        self.state.mark_stopped()

    def save_snapshot(self):
        """保存唯一最新帧对应的所有调试数据。"""
        with self._snapshot_lock:
            payload = self.state.snapshot_payload()
            if payload is None:
                raise SnapshotUnavailable("No processed frame is available yet")
            sequence, result, artifacts = payload
            root = self.web_config["snapshot_output_dir"]
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_name = "{}_frame_{:06d}".format(timestamp, sequence)
            output_dir = os.path.join(root, base_name)
            suffix = 1
            while os.path.exists(output_dir):
                output_dir = os.path.join(
                    root, "{}_{}".format(base_name, suffix))
                suffix += 1
            save_detection_artifacts(output_dir, result, artifacts)
            self.state.set_last_snapshot(output_dir)
            return output_dir


class ThreadingPreviewHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _handler_class(service):
    class PreviewRequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def _send_bytes(self, content, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def _send_json(self, payload, status=200):
            content = json.dumps(
                payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self._send_bytes(content, "application/json; charset=utf-8", status)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self._send_bytes(
                    INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/status":
                self._send_json(service.state.status_dict())
            elif path == "/stream.mjpg":
                self._stream_mjpeg()
            elif path == "/favicon.ico":
                self._send_bytes(b"", "image/x-icon", status=204)
            else:
                self._send_json({"ok": False, "message": "Not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            if path != "/api/snapshot":
                self._send_json({"ok": False, "message": "Not found"}, 404)
                return
            try:
                output_dir = service.save_snapshot()
            except SnapshotUnavailable as exc:
                self._send_json(
                    {"ok": False, "message": str(exc)}, status=409)
            except (IOError, OSError, RuntimeError) as exc:
                LOGGER.exception("Snapshot save failed")
                self._send_json(
                    {"ok": False, "message": str(exc)}, status=500)
            else:
                self._send_json({"ok": True, "path": output_dir})

        def _stream_mjpeg(self):
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary={}".format(
                    MJPEG_BOUNDARY))
            self.send_header("Cache-Control", "no-store, no-cache")
            self.end_headers()
            last_sequence = -1
            service.state.change_clients(1)
            try:
                while True:
                    sequence, jpeg, running = service.state.wait_for_jpeg(
                        last_sequence,
                        service.web_config["stream_wait_timeout_s"])
                    if jpeg is None:
                        if not running:
                            break
                        continue
                    if sequence == last_sequence:
                        if not running:
                            break
                        continue
                    header = (
                        "--{}\r\nContent-Type: image/jpeg\r\n"
                        "Content-Length: {}\r\n\r\n".format(
                            MJPEG_BOUNDARY, len(jpeg))).encode("ascii")
                    self.wfile.write(header)
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                    last_sequence = sequence
                    if not running:
                        break
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            finally:
                service.state.change_clients(-1)

        def log_message(self, format_string, *args):
            LOGGER.debug("HTTP %s - %s", self.address_string(),
                         format_string % args)

    return PreviewRequestHandler


def create_preview_server(service, host=None, port=None):
    """创建 HTTP 服务；测试可传 ``port=0`` 由系统选择空闲端口。"""
    bind_host = service.web_config["host"] if host is None else host
    bind_port = service.web_config["port"] if port is None else port
    return ThreadingPreviewHTTPServer(
        (bind_host, bind_port), _handler_class(service))


def run_web_preview(camera_config, web_config=None, camera_factory=None):
    """阻塞运行浏览器预览，按 Ctrl+C 后释放 HTTP 和摄像头资源。"""
    config = get_web_config(web_config)
    camera = CameraReader(camera_config, capture_factory=camera_factory)
    service = PreviewService(camera, config)
    server = None
    try:
        service.start()
        server = create_preview_server(service)
        host, port = server.server_address[:2]
        print("Web preview listening on http://{}:{}".format(host, port))
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("Stopping web preview")
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        service.stop()
