"""在 Nano 上从 USB 摄像头采集静态目标原图。"""

import argparse
import json
import os
import sys
import time


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import cv2  # noqa: E402

from config import get_camera_config  # noqa: E402
from src.camera import CameraError, CameraReader  # noqa: E402


def _camera_device(value):
    try:
        return int(value)
    except ValueError:
        return value


def _number_label(value):
    if value is None:
        return "unknown"
    return ("{:.2f}".format(value).rstrip("0").rstrip(".")
            .replace(".", "p"))


def _unique_image_path(output_dir, prefix):
    for index in range(1, 10000):
        path = os.path.join(output_dir, "{}_{:03d}.jpg".format(prefix, index))
        if not os.path.exists(path):
            return path
    raise RuntimeError("Too many capture files with prefix {}".format(prefix))


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Capture raw static target images from the Nano USB camera.")
    parser.add_argument("--output", default="outputs/static_targets")
    parser.add_argument(
        "--shape", choices=("circle", "square", "triangle", "unknown"),
        default="unknown")
    parser.add_argument("--size-cm", type=float)
    parser.add_argument("--distance-cm", type=float)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--delay-s", type=float, default=2.0)
    parser.add_argument("--interval-s", type=float, default=0.5)
    parser.add_argument("--device", type=_camera_device, default=0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--warmup-frames", type=int, default=30)
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)
    if args.count <= 0:
        print("--count must be positive", file=sys.stderr)
        return 1
    if args.delay_s < 0 or args.interval_s < 0:
        print("capture delays must be non-negative", file=sys.stderr)
        return 1
    if args.size_cm is not None and args.size_cm <= 0:
        print("--size-cm must be positive", file=sys.stderr)
        return 1
    if args.distance_cm is not None and args.distance_cm <= 0:
        print("--distance-cm must be positive", file=sys.stderr)
        return 1

    if not os.path.isdir(args.output):
        os.makedirs(args.output)
    config = get_camera_config({
        "device": args.device,
        "width": args.width,
        "height": args.height,
        "fps": args.fps,
        "warmup_frames": args.warmup_frames,
    })
    camera = CameraReader(config)
    manifest_path = os.path.join(args.output, "captures.jsonl")
    try:
        settings = camera.open()
        print(json.dumps(
            {"event": "camera_opened", "actual": settings},
            ensure_ascii=False, sort_keys=True))
        camera.warmup()
        if args.delay_s > 0:
            time.sleep(args.delay_s)

        timestamp_label = time.strftime("%Y%m%d_%H%M%S")
        prefix = "{}_{}cm_{}cm_{}".format(
            args.shape,
            _number_label(args.size_cm),
            _number_label(args.distance_cm),
            timestamp_label)
        for index in range(args.count):
            ok, frame, timestamp = camera.read()
            if not ok:
                raise CameraError(camera.last_error or "Camera read failed")
            image_path = _unique_image_path(args.output, prefix)
            if not cv2.imwrite(image_path, frame):
                raise IOError("Cannot save image: {}".format(image_path))
            record = {
                "timestamp": float(timestamp),
                "image": os.path.basename(image_path),
                "shape": args.shape,
                "size_cm": args.size_cm,
                "distance_cm": args.distance_cm,
                "camera": settings,
            }
            with open(manifest_path, "a", encoding="utf-8") as manifest:
                manifest.write(json.dumps(
                    record, ensure_ascii=False, sort_keys=True) + "\n")
            print(json.dumps(record, ensure_ascii=False, sort_keys=True))
            if index + 1 < args.count and args.interval_s > 0:
                time.sleep(args.interval_s)
    except (CameraError, IOError, OSError, RuntimeError, ValueError) as exc:
        print("capture failed: {}".format(exc), file=sys.stderr)
        return 1
    finally:
        camera.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
