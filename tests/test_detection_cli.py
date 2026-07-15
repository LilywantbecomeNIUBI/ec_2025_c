"""静态图片检测命令行工具集成测试。"""

import contextlib
import io
import json
import os
import tempfile
import unittest

import cv2

from scripts import detection_test
from tests.synthetic_targets import create_target_scene


class DetectionCliTest(unittest.TestCase):
    def test_success_writes_json_and_debug_images(self):
        frame, _corners = create_target_scene("square")
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "target.jpg")
            output_dir = os.path.join(temp_dir, "result")
            self.assertTrue(cv2.imwrite(input_path, frame))

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = detection_test.main([
                    "--input", input_path,
                    "--output", output_dir,
                ])

            self.assertEqual(exit_code, 0)
            for filename in (
                    "original.jpg", "binary.jpg", "edges.jpg",
                    "board_corners.jpg",
                    "rectified.jpg", "shape_contours.jpg",
                    "final_overlay.jpg", "result.json"):
                self.assertTrue(os.path.isfile(
                    os.path.join(output_dir, filename)), msg=filename)
            with open(os.path.join(output_dir, "result.json"),
                      "r", encoding="utf-8") as result_file:
                result = json.load(result_file)
            self.assertTrue(result["ok"])
            self.assertEqual(result["shape"], "square")


if __name__ == "__main__":
    unittest.main()
