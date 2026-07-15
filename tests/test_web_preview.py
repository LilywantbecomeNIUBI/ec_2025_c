"""浏览器实时预览、MJPEG、状态 API 和快照测试。"""

import json
import os
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen

from src.web_preview import INDEX_HTML, MJPEG_BOUNDARY
from src.web_preview import PreviewService, create_preview_server
from tests.synthetic_targets import create_target_scene


class FakeCamera(object):
    def __init__(self, frame):
        self.frame = frame
        self.last_error = ""
        self.opened = False
        self.warmed_up = False
        self.released = False

    def open(self):
        self.opened = True
        self.released = False
        return {"device": 0, "width": 640.0, "height": 480.0, "fps": 30.0}

    def warmup(self):
        self.warmed_up = True

    def read(self):
        return True, self.frame.copy(), time.time()

    def release(self):
        self.released = True
        self.opened = False


def wait_for_sequence(service, minimum=1, timeout_s=3.0):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = service.state.status_dict()
        if status["sequence"] >= minimum:
            return status
        time.sleep(0.02)
    raise AssertionError("preview did not publish a frame")


class PreviewServiceTest(unittest.TestCase):
    def test_service_publishes_only_latest_jpeg_and_releases_camera(self):
        frame, _corners = create_target_scene("square")
        camera = FakeCamera(frame)
        service = PreviewService(camera, {
            "host": "127.0.0.1",
            "port": 8000,
            "preview_fps": 20.0,
            "jpeg_quality": 75,
        })

        service.start()
        try:
            status = wait_for_sequence(service)
            sequence, jpeg, running = service.state.wait_for_jpeg(-1, 0.2)
            self.assertTrue(camera.warmed_up)
            self.assertTrue(running)
            self.assertGreaterEqual(sequence, 1)
            self.assertTrue(jpeg.startswith(b"\xff\xd8"))
            self.assertEqual(status["result"]["shape"], "square")
            self.assertGreater(status["processing_ms"], 0.0)
        finally:
            service.stop()

        self.assertTrue(camera.released)
        self.assertFalse(service.state.status_dict()["running"])

    def test_http_page_status_stream_snapshot_and_disconnect(self):
        frame, _corners = create_target_scene("triangle")
        camera = FakeCamera(frame)
        with tempfile.TemporaryDirectory() as temp_dir:
            service = PreviewService(camera, {
                "host": "127.0.0.1",
                "port": 8000,
                "preview_fps": 20.0,
                "jpeg_quality": 75,
                "snapshot_output_dir": temp_dir,
            })
            service.start()
            wait_for_sequence(service)
            server = create_preview_server(service, host="127.0.0.1", port=0)
            server_thread = threading.Thread(
                target=server.serve_forever, daemon=True)
            server_thread.start()
            host, port = server.server_address[:2]
            base_url = "http://{}:{}".format(host, port)
            try:
                with urlopen(base_url + "/", timeout=2.0) as response:
                    page = response.read().decode("utf-8")
                self.assertIn("EC_2025_C · 实时视觉调试", page)
                self.assertIn("/stream.mjpg", page)
                self.assertIn("/api/snapshot", page)

                with urlopen(base_url + "/api/status", timeout=2.0) as response:
                    status = json.loads(response.read().decode("utf-8"))
                self.assertTrue(status["running"])
                self.assertEqual(status["result"]["shape"], "triangle")

                stream_one = urlopen(base_url + "/stream.mjpg", timeout=2.0)
                stream_two = urlopen(base_url + "/stream.mjpg", timeout=2.0)
                prefix_one = stream_one.read(256)
                prefix_two = stream_two.read(256)
                for stream_prefix in (prefix_one, prefix_two):
                    self.assertIn(
                        MJPEG_BOUNDARY.encode("ascii"), stream_prefix)
                    self.assertIn(b"Content-Type: image/jpeg", stream_prefix)
                stream_one.close()
                stream_two.close()
                self.assertTrue(service.running)

                request = Request(
                    base_url + "/api/snapshot", data=b"", method="POST")
                with urlopen(request, timeout=3.0) as response:
                    snapshot = json.loads(response.read().decode("utf-8"))
                self.assertTrue(snapshot["ok"])
                self.assertTrue(os.path.isfile(os.path.join(
                    snapshot["path"], "result.json")))
                self.assertTrue(os.path.isfile(os.path.join(
                    snapshot["path"], "final_overlay.jpg")))
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=2.0)
                service.stop()

    def test_page_has_no_external_asset_dependency(self):
        self.assertNotIn("https://", INDEX_HTML)
        self.assertNotIn("<script src=", INDEX_HTML)


if __name__ == "__main__":
    unittest.main()
