"""2025 年电赛 C 题复现项目的阶段 2A 摄像头入口。"""

import argparse
import json
import sys

from config import get_camera_config
from src.camera import CameraError, CameraReader
from src.detection import process_frame


def _camera_device(value):
    """允许 ``0`` 或 ``/dev/video0`` 两种摄像头写法。"""
    try:
        return int(value)
    except ValueError:
        return value


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Open, warm up, and read frames from the USB camera.")
    parser.add_argument("--device", type=_camera_device, default=0,
                        help="camera index or device path (default: 0)")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--warmup-frames", type=int, default=30)
    parser.add_argument("--frames", type=int, default=1,
                        help="number of checked frames after warm-up")
    parser.add_argument("--skip-warmup", action="store_true")
    return parser


def run_camera_check(camera_config, frame_count=1, skip_warmup=False,
                     camera_factory=None):
    """执行摄像头检查并返回每帧的统一结果。"""
    if isinstance(frame_count, bool) or not isinstance(frame_count, int):
        raise ValueError("frame_count must be a positive integer")
    if frame_count <= 0:
        raise ValueError("frame_count must be a positive integer")

    camera = CameraReader(camera_config, capture_factory=camera_factory)
    results = []
    try:
        settings = camera.open()
        print(json.dumps(
            {"event": "camera_opened", "actual": settings},
            ensure_ascii=False,
            sort_keys=True))
        if not skip_warmup:
            camera.warmup()
            print(json.dumps(
                {"event": "camera_warmup_complete",
                 "frames": camera.config["warmup_frames"]},
                ensure_ascii=False,
                sort_keys=True))

        for _index in range(frame_count):
            ok, frame, timestamp = camera.read()
            if not ok:
                raise CameraError(camera.last_error or "Camera read failed")
            result = process_frame(frame, timestamp)
            results.append(result)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return results
    finally:
        camera.release()


def main(argv=None):
    """解析命令行并运行摄像头检查。"""
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        config = get_camera_config({
            "device": args.device,
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "warmup_frames": args.warmup_frames,
        })
        run_camera_check(
            config,
            frame_count=args.frames,
            skip_warmup=args.skip_warmup)
    except (CameraError, ValueError) as exc:
        print("camera check failed: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
