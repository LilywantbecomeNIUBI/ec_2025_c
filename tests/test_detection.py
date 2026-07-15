"""阶段 2A 单帧处理和统一结果测试。"""

import unittest

from src.detection import process_frame
from src.result import create_result


class FakeFrame(object):
    shape = (480, 640, 3)


class DetectionEntryTest(unittest.TestCase):
    def test_valid_frame_reports_preview_ready_without_fake_measurements(self):
        result = process_frame(FakeFrame(), timestamp=12.5)

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "frame_ready")
        self.assertEqual(result["timestamp"], 12.5)
        self.assertIsNone(result["shape"])
        self.assertIsNone(result["distance_cm"])
        self.assertIsNone(result["size_cm"])
        self.assertEqual(result["debug"]["frame_shape"], [480, 640, 3])
        self.assertEqual(result["debug"]["frame_center_px"], [320.0, 240.0])

    def test_none_frame_has_explicit_failure_status(self):
        result = process_frame(None, timestamp=1.0)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "invalid_frame")

    def test_result_containers_are_not_shared(self):
        first = create_result(timestamp=1.0)
        second = create_result(timestamp=2.0)
        first["board_corners_px"].append([1.0, 2.0])
        first["quality"]["board_score"] = 0.5

        self.assertEqual(second["board_corners_px"], [])
        self.assertIsNone(second["quality"]["board_score"])


if __name__ == "__main__":
    unittest.main()
