"""CameraReader 无硬件单元测试。"""

import unittest

from config import get_camera_config
from src.camera import CameraError, CameraReader


class FakeFrame(object):
    shape = (480, 640, 3)


class FakeCapture(object):
    def __init__(self, frames=None, opened=True):
        self.frames = list(frames or [])
        self.opened = opened
        self.released = False
        self.properties = {}

    def isOpened(self):
        return self.opened and not self.released

    def set(self, property_id, value):
        self.properties[property_id] = value
        return True

    def get(self, property_id):
        return self.properties.get(property_id, 0.0)

    def read(self):
        if not self.frames:
            return False, None
        return self.frames.pop(0)

    def release(self):
        self.released = True


def test_config(**overrides):
    values = {
        "warmup_frames": 0,
        "warmup_delay_s": 0.0,
        "read_failure_limit": 1,
        "reconnect_attempts": 1,
        "reconnect_delay_s": 0.0,
    }
    values.update(overrides)
    return get_camera_config(values)


class CameraReaderTest(unittest.TestCase):
    def test_open_applies_requested_properties(self):
        capture = FakeCapture([(True, FakeFrame())])
        reader = CameraReader(
            test_config(), capture_factory=lambda _device: capture)

        settings = reader.open()

        self.assertTrue(reader.is_opened)
        self.assertEqual(capture.properties[3], 640)
        self.assertEqual(capture.properties[4], 480)
        self.assertEqual(capture.properties[5], 30)
        self.assertEqual(settings["width"], 640.0)
        reader.release()
        self.assertTrue(capture.released)

    def test_warmup_discards_frames_then_read_returns_timestamp(self):
        frames = [
            (True, FakeFrame()),
            (True, FakeFrame()),
            (True, FakeFrame()),
        ]
        capture = FakeCapture(frames)
        timestamps = iter([1.0, 2.0, 3.0])
        reader = CameraReader(
            test_config(warmup_frames=2),
            capture_factory=lambda _device: capture,
            clock_fn=lambda: next(timestamps))
        reader.open()

        reader.warmup()
        ok, frame, timestamp = reader.read()

        self.assertTrue(ok)
        self.assertIsInstance(frame, FakeFrame)
        self.assertEqual(timestamp, 3.0)

    def test_failed_read_reconnects_and_retries_once(self):
        first = FakeCapture([(False, None)])
        second = FakeCapture([(True, FakeFrame())])
        captures = iter([first, second])
        reader = CameraReader(
            test_config(),
            capture_factory=lambda _device: next(captures),
            clock_fn=lambda: 10.0)
        reader.open()

        ok, frame, timestamp = reader.read()

        self.assertTrue(ok)
        self.assertIsInstance(frame, FakeFrame)
        self.assertEqual(timestamp, 10.0)
        self.assertTrue(first.released)

    def test_open_failure_releases_failed_capture(self):
        capture = FakeCapture(opened=False)
        reader = CameraReader(
            test_config(), capture_factory=lambda _device: capture)

        with self.assertRaises(CameraError):
            reader.open()

        self.assertTrue(capture.released)

    def test_context_manager_always_releases(self):
        capture = FakeCapture()
        reader = CameraReader(
            test_config(), capture_factory=lambda _device: capture)

        with reader:
            self.assertTrue(reader.is_opened)

        self.assertTrue(capture.released)


class CameraConfigTest(unittest.TestCase):
    def test_config_is_copied(self):
        first = get_camera_config()
        first["width"] = 1
        second = get_camera_config()
        self.assertEqual(second["width"], 640)

    def test_unknown_config_key_is_rejected(self):
        with self.assertRaises(ValueError):
            get_camera_config({"unknown": 1})

    def test_invalid_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            get_camera_config({"width": 0})


if __name__ == "__main__":
    unittest.main()
