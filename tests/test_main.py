"""阶段 2A 命令入口的无硬件集成测试。"""

import io
import json
import unittest
from contextlib import redirect_stdout

from config import get_camera_config
from main import run_camera_check


class FakeFrame(object):
    shape = (480, 640, 3)


class FakeCapture(object):
    def __init__(self):
        self.released = False
        self.properties = {}

    def isOpened(self):
        return not self.released

    def set(self, property_id, value):
        self.properties[property_id] = value
        return True

    def get(self, property_id):
        return self.properties.get(property_id, 0.0)

    def read(self):
        return True, FakeFrame()

    def release(self):
        self.released = True


class CameraEntryIntegrationTest(unittest.TestCase):
    def test_camera_check_outputs_json_and_releases_capture(self):
        capture = FakeCapture()
        config = get_camera_config({
            "warmup_frames": 0,
            "warmup_delay_s": 0.0,
        })
        output = io.StringIO()

        with redirect_stdout(output):
            results = run_camera_check(
                config,
                frame_count=1,
                camera_factory=lambda _device: capture)

        lines = output.getvalue().strip().splitlines()
        opened_event = json.loads(lines[0])
        frame_result = json.loads(lines[-1])
        self.assertEqual(opened_event["event"], "camera_opened")
        self.assertEqual(frame_result["status"], "frame_ready")
        self.assertEqual(results[0]["status"], "frame_ready")
        self.assertTrue(capture.released)


if __name__ == "__main__":
    unittest.main()
