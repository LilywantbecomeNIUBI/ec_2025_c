"""阶段 3 A4 目标纸与基本形状检测测试。"""

import unittest

import cv2
import numpy as np

from src.detection import analyze_frame, process_frame
from src.geometry import order_corners
from src.result import create_result
from tests.synthetic_targets import create_target_scene


class StaticTargetDetectionTest(unittest.TestCase):
    def test_three_basic_shapes_are_classified(self):
        for expected_shape in ("circle", "square", "triangle"):
            frame, expected_corners = create_target_scene(expected_shape)
            result, artifacts = analyze_frame(frame, timestamp=12.5)

            self.assertTrue(result["ok"], msg=(expected_shape, result))
            self.assertEqual(result["shape"], expected_shape)
            self.assertGreaterEqual(result["shape_confidence"], 0.65)
            self.assertIsNone(result["distance_cm"])
            self.assertIsNone(result["size_cm"])
            self.assertIn("rectified", artifacts)
            self.assertIn("final_overlay", artifacts)
            actual_corners = np.asarray(result["board_corners_px"])
            corner_error = np.mean(np.linalg.norm(
                actual_corners - order_corners(expected_corners), axis=1))
            self.assertLess(corner_error, 10.0)

    def test_non_square_rectangle_is_not_forced_into_a_class(self):
        frame, _corners = create_target_scene("rectangle")
        result = process_frame(frame)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "shape_unknown")
        self.assertIsNone(result["shape"])

    def test_board_not_found_has_explicit_status_and_debug_images(self):
        frame = np.full((480, 640, 3), 180, dtype=np.uint8)
        result, artifacts = analyze_frame(frame, timestamp=1.0)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "board_not_found")
        self.assertIn("binary", artifacts)
        self.assertIn("final_overlay", artifacts)

    def test_invalid_frame_is_rejected(self):
        result = process_frame(None, timestamp=1.0)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "invalid_frame")

    def test_grayscale_frame_is_supported(self):
        color, _corners = create_target_scene("circle")
        gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
        result = process_frame(gray)

        self.assertTrue(result["ok"])
        self.assertEqual(result["shape"], "circle")

    def test_result_containers_are_not_shared(self):
        first = create_result(timestamp=1.0)
        second = create_result(timestamp=2.0)
        first["board_corners_px"].append([1.0, 2.0])
        first["quality"]["board_score"] = 0.5

        self.assertEqual(second["board_corners_px"], [])
        self.assertIsNone(second["quality"]["board_score"])


if __name__ == "__main__":
    unittest.main()
