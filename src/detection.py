"""A4 目标纸、透视矫正和基本形状的单帧处理入口。"""

import cv2

from config import get_vision_config
from src.board_detector import detect_target_board
from src.geometry import map_point_to_source, rectify_board
from src.result import create_result
from src.shape_detector import detect_basic_shape
from src.visualization import draw_detection_overlay, draw_shape_overlay


def _valid_frame_shape(frame):
    shape = getattr(frame, "shape", None)
    if shape is None or len(shape) < 2:
        return None
    height = int(shape[0])
    width = int(shape[1])
    if width <= 0 or height <= 0:
        return None
    channels = int(shape[2]) if len(shape) >= 3 else 1
    return height, width, channels


def _corners_to_list(corners):
    return [[float(point[0]), float(point[1])] for point in corners]


def analyze_frame(frame, timestamp=None, vision_config=None):
    """完成一帧静态目标检测，返回 ``(result, artifacts)``。"""
    frame_shape = _valid_frame_shape(frame)
    if frame_shape is None:
        result = create_result(
            ok=False,
            status="invalid_frame",
            message="Frame has no valid image dimensions",
            timestamp=timestamp)
        return result, {}

    config = get_vision_config(vision_config)
    height, width, channels = frame_shape
    base_debug = {
        "frame_shape": [height, width, channels],
        "frame_center_px": [width / 2.0, height / 2.0],
    }
    artifacts = {"original": frame.copy()}
    board = detect_target_board(frame, config)
    artifacts.update(board.get("debug", {}))
    if not board["ok"]:
        debug = dict(base_debug)
        debug["board_candidate_count"] = len(board.get("candidates", []))
        result = create_result(
            ok=False,
            status=board["status"],
            message=board["message"],
            timestamp=timestamp,
            debug=debug)
        artifacts["final_overlay"] = draw_detection_overlay(frame, result)
        return result, artifacts

    corners = board["corners"]
    board_corners = _corners_to_list(corners)
    board_overlay_result = create_result(
        ok=False, status="shape_not_processed", timestamp=timestamp)
    board_overlay_result["board_corners_px"] = board_corners
    artifacts["board_corners"] = draw_detection_overlay(
        frame, board_overlay_result)

    try:
        rectified, homography = rectify_board(
            frame, corners, config["board"])
    except (cv2.error, ValueError) as exc:
        debug = dict(base_debug)
        debug["rectification_error"] = str(exc)
        result = create_result(
            ok=False,
            status="rectification_failed",
            message="Perspective rectification failed",
            timestamp=timestamp,
            debug=debug)
        result["board_corners_px"] = board_corners
        result["quality"]["board_score"] = float(board["score"])
        artifacts["final_overlay"] = draw_detection_overlay(frame, result)
        return result, artifacts

    artifacts["rectified"] = rectified
    shape_result = detect_basic_shape(rectified, config)
    artifacts.update(shape_result.get("debug", {}))
    artifacts["shape_contours"] = draw_shape_overlay(rectified, shape_result)

    debug = dict(base_debug)
    debug.update({
        "board_candidate_count": len(board.get("candidates", [])),
        "board_aspect_ratio": float(board["aspect_ratio"]),
        "board_border_contrast": float(board["border_contrast"]),
        "rectified_shape": [int(value) for value in rectified.shape],
    })
    if "scores" in shape_result:
        debug["shape_scores"] = {
            key: float(value) for key, value in shape_result["scores"].items()
        }
        debug["shape_features"] = shape_result["features"]
        debug["shape_size_px"] = shape_result["size_px"]

    result = create_result(
        ok=shape_result["ok"],
        status="ok" if shape_result["ok"] else shape_result["status"],
        message=shape_result["message"],
        timestamp=timestamp,
        debug=debug)
    result["board_corners_px"] = board_corners
    result["quality"]["board_score"] = float(board["score"])
    if "confidence" in shape_result:
        result["quality"]["shape_score"] = float(
            shape_result["confidence"])
        result["shape_confidence"] = float(shape_result["confidence"])

    if shape_result["ok"]:
        source_center = map_point_to_source(
            shape_result["center"], homography)
        center_px = [float(source_center[0]), float(source_center[1])]
        result["shape"] = shape_result["shape"]
        result["center_px"] = center_px
        result["dx_px"] = center_px[0] - width / 2.0
        result["dy_px"] = center_px[1] - height / 2.0

    artifacts["final_overlay"] = draw_detection_overlay(frame, result)
    return result, artifacts


def process_frame(frame, timestamp=None, vision_config=None):
    """执行单帧检测并只返回统一结果。"""
    result, _artifacts = analyze_frame(frame, timestamp, vision_config)
    return result
