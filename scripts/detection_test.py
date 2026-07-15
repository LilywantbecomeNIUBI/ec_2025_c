"""从静态图片检测 A4 黑框、透视图和基本形状。"""

import argparse
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np  # noqa: E402

from src.artifacts import save_detection_artifacts  # noqa: E402
from src.detection import analyze_frame  # noqa: E402


def read_image(path):
    """兼容 Windows 中文路径的图片读取。"""
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except (IOError, OSError):
        return None
    if data.size == 0:
        return None
    import cv2
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


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
    save_detection_artifacts(args.output, result, artifacts)
    import json
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
