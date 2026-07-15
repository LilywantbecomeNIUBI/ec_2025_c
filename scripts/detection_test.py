"""从静态图片检测 A4 黑框、透视图和基本形状。"""

import argparse
import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from src.detection import analyze_frame  # noqa: E402


ARTIFACT_FILENAMES = {
    "original": "original.jpg",
    "gray": "gray.jpg",
    "binary": "binary.jpg",
    "edges": "edges.jpg",
    "board_candidates": "board_candidates.jpg",
    "board_corners": "board_corners.jpg",
    "rectified": "rectified.jpg",
    "shape_binary": "shape_binary.jpg",
    "shape_contours": "shape_contours.jpg",
    "final_overlay": "final_overlay.jpg",
}


def read_image(path):
    """兼容 Windows 中文路径的图片读取。"""
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except (IOError, OSError):
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image(path, image):
    """兼容 Windows 中文路径的图片保存。"""
    extension = os.path.splitext(path)[1] or ".jpg"
    ok, encoded = cv2.imencode(extension, image)
    if not ok:
        raise IOError("Cannot encode image: {}".format(path))
    encoded.tofile(path)


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Detect the A4 target board and basic shape in one image.")
    parser.add_argument("--input", required=True, help="input image path")
    parser.add_argument(
        "--output", required=True,
        help="output directory for debug images and result.json")
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)
    image = read_image(args.input)
    if image is None:
        print("cannot read input image: {}".format(args.input), file=sys.stderr)
        return 1

    if not os.path.isdir(args.output):
        os.makedirs(args.output)
    result, artifacts = analyze_frame(image)
    for name, filename in ARTIFACT_FILENAMES.items():
        artifact = artifacts.get(name)
        if artifact is not None:
            write_image(os.path.join(args.output, filename), artifact)

    result_path = os.path.join(args.output, "result.json")
    with open(result_path, "w", encoding="utf-8") as result_file:
        json.dump(result, result_file, ensure_ascii=False, indent=2,
                  sort_keys=True)
        result_file.write("\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
