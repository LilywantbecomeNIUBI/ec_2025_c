"""带 2 cm 黑框的竖版 A4 目标纸检测。"""

import cv2
import numpy as np

from src.geometry import angle_cosines, contour_center, edge_lengths
from src.geometry import find_contours, order_corners


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


def _threshold_images(gray, preprocess_config):
    blur_size = preprocess_config["blur_kernel"]
    blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    _threshold, otsu = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    block_size = preprocess_config["adaptive_block_size"]
    adaptive = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block_size, preprocess_config["adaptive_c"])
    kernel_size = preprocess_config["morph_kernel"]
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    return [
        ("otsu", cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)),
        ("adaptive", cv2.morphologyEx(
            adaptive, cv2.MORPH_CLOSE, kernel)),
    ]


def _border_contrast(gray, corners, ring_ratio):
    height, width = gray.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    polygon = np.round(corners).astype(np.int32)
    cv2.fillConvexPoly(mask, polygon, 255)
    lengths = edge_lengths(corners)
    ring_width = max(3, int(round(min(lengths) * ring_ratio)))
    kernel_size = ring_width * 2 + 1
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    inside = cv2.erode(mask, kernel)
    outside = cv2.subtract(cv2.dilate(mask, kernel), mask)
    inside_pixels = gray[inside > 0]
    outside_pixels = gray[outside > 0]
    if inside_pixels.size == 0 or outside_pixels.size == 0:
        return -255.0
    return float(np.mean(inside_pixels) - np.mean(outside_pixels))


def _candidate_from_contour(contour, gray, image_area, image_center,
                            image_diagonal, config, threshold_name):
    area = float(cv2.contourArea(contour))
    area_ratio = area / image_area
    if not config["min_area_ratio"] <= area_ratio <= config["max_area_ratio"]:
        return None

    perimeter = float(cv2.arcLength(contour, True))
    if perimeter <= 1.0:
        return None
    approximation = cv2.approxPolyDP(
        contour, config["approx_epsilon_ratio"] * perimeter, True)
    if len(approximation) != 4 or not cv2.isContourConvex(approximation):
        return None

    corners = order_corners(approximation.reshape(4, 2))
    margin = config["edge_margin_px"]
    height, width = gray.shape[:2]
    if (np.min(corners[:, 0]) < margin or np.min(corners[:, 1]) < margin or
            np.max(corners[:, 0]) > width - 1 - margin or
            np.max(corners[:, 1]) > height - 1 - margin):
        return None

    lengths = edge_lengths(corners)
    horizontal = (lengths[0] + lengths[2]) / 2.0
    vertical = (lengths[1] + lengths[3]) / 2.0
    if horizontal <= 1.0 or vertical <= horizontal:
        return None
    aspect_ratio = vertical / horizontal
    if not config["aspect_ratio_min"] <= aspect_ratio <= config["aspect_ratio_max"]:
        return None

    max_angle_cosine = max(angle_cosines(corners))
    if max_angle_cosine > config["max_angle_cosine"]:
        return None

    rotated_rect = cv2.minAreaRect(contour)
    rect_area = float(rotated_rect[1][0] * rotated_rect[1][1])
    fill_ratio = area / rect_area if rect_area > 1.0 else 0.0
    if fill_ratio < config["min_fill_ratio"]:
        return None

    contrast = _border_contrast(
        gray, corners, config["border_ring_ratio"])
    if contrast < config["min_border_contrast"]:
        return None

    center = contour_center(contour)
    if center is None:
        return None
    center_distance = float(np.linalg.norm(center - image_center))
    target_ratio = config["inner_height_mm"] / config["inner_width_mm"]
    ratio_span = max(
        target_ratio - config["aspect_ratio_min"],
        config["aspect_ratio_max"] - target_ratio)
    ratio_score = _clamp01(1.0 - abs(aspect_ratio - target_ratio) / ratio_span)
    area_score = _clamp01(area_ratio / 0.25)
    angle_score = _clamp01(
        1.0 - max_angle_cosine / config["max_angle_cosine"])
    contrast_score = _clamp01(contrast / 100.0)
    center_score = _clamp01(1.0 - center_distance / (0.5 * image_diagonal))
    score = (0.30 * ratio_score + 0.20 * area_score +
             0.20 * angle_score + 0.20 * contrast_score +
             0.10 * center_score)
    return {
        "corners": corners,
        "center": center,
        "score": float(score),
        "area_ratio": area_ratio,
        "aspect_ratio": aspect_ratio,
        "max_angle_cosine": max_angle_cosine,
        "fill_ratio": fill_ratio,
        "border_contrast": contrast,
        "threshold": threshold_name,
    }


def _refine_corners(gray, corners, config):
    window = config["subpixel_window_px"]
    original = np.asarray(corners, dtype=np.float32).reshape(4, 1, 2)
    refined = original.copy()
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.01,
    )
    try:
        cv2.cornerSubPix(
            gray, refined, (window, window), (-1, -1), criteria)
    except cv2.error:
        return original.reshape(4, 2)
    shifts = np.linalg.norm(
        refined.reshape(4, 2) - original.reshape(4, 2), axis=1)
    if float(np.max(shifts)) > config["max_subpixel_shift_px"]:
        return original.reshape(4, 2)
    return order_corners(refined.reshape(4, 2))


def detect_target_board(frame, vision_config):
    """检测黑框内部白色矩形并返回四角和调试图。"""
    if frame is None or len(frame.shape) < 2:
        return {
            "ok": False,
            "status": "invalid_frame",
            "message": "Frame is invalid",
            "candidates": [],
            "debug": {},
        }
    if len(frame.shape) == 2:
        gray = frame.copy()
    else:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    image_area = float(height * width)
    image_center = np.array([width / 2.0, height / 2.0], dtype=np.float32)
    image_diagonal = float(np.hypot(width, height))
    board_config = vision_config["board"]
    threshold_images = _threshold_images(gray, vision_config["preprocess"])
    candidates = []

    for threshold_name, binary in threshold_images:
        contours, _hierarchy = find_contours(binary, cv2.RETR_LIST)
        for contour in contours:
            candidate = _candidate_from_contour(
                contour, gray, image_area, image_center, image_diagonal,
                board_config, threshold_name)
            if candidate is not None:
                candidates.append(candidate)

    candidate_image = frame.copy()
    for candidate in candidates:
        polygon = np.round(candidate["corners"]).astype(np.int32)
        cv2.polylines(candidate_image, [polygon], True, (0, 165, 255), 1)

    debug = {
        "gray": gray,
        "binary": threshold_images[0][1],
        "edges": cv2.Canny(
            gray,
            vision_config["preprocess"]["canny_low"],
            vision_config["preprocess"]["canny_high"]),
        "board_candidates": candidate_image,
    }
    if not candidates:
        return {
            "ok": False,
            "status": "board_not_found",
            "message": "No valid A4 inner rectangle candidate",
            "candidates": [],
            "debug": debug,
        }

    candidates.sort(key=lambda item: item["score"], reverse=True)
    unique_candidates = []
    duplicate_distance = board_config["duplicate_corner_distance_px"]
    for candidate in candidates:
        is_duplicate = False
        for existing in unique_candidates:
            mean_distance = float(np.mean(np.linalg.norm(
                candidate["corners"] - existing["corners"], axis=1)))
            if mean_distance <= duplicate_distance:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_candidates.append(candidate)

    if (len(unique_candidates) > 1 and
            unique_candidates[0]["score"] - unique_candidates[1]["score"] <
            board_config["ambiguity_score_margin"]):
        return {
            "ok": False,
            "status": "board_ambiguous",
            "message": "Multiple A4 board candidates have similar quality",
            "candidates": unique_candidates,
            "debug": debug,
        }

    best = dict(unique_candidates[0])
    best["corners"] = _refine_corners(gray, best["corners"], board_config)
    best["center"] = np.mean(best["corners"], axis=0)
    best["ok"] = True
    best["status"] = "ok"
    best["message"] = ""
    best["candidates"] = unique_candidates
    best["debug"] = debug
    return best
