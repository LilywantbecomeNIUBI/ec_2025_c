"""透视矫正图中的圆形、正方形和等边三角形识别。"""

import math

import cv2
import numpy as np

from src.geometry import angle_cosines, contour_center, edge_lengths
from src.geometry import find_contours, interior_angles_deg


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


def _ratio_score(value, best, worst):
    if worst <= best:
        return 0.0
    return _clamp01(1.0 - (float(value) - best) / (worst - best))


def _circle_score(features, config):
    if features["vertices"] < 6 or not features["convex"]:
        return 0.0
    circularity_score = _clamp01(
        (features["circularity"] - config["circle_min_circularity"]) /
        (1.0 - config["circle_min_circularity"]))
    axis_score = _clamp01(
        (features["ellipse_axis_ratio"] - config["circle_min_axis_ratio"]) /
        (1.0 - config["circle_min_axis_ratio"]))
    vertices_score = _clamp01((features["vertices"] - 5.0) / 5.0)
    return float(
        0.45 * circularity_score + 0.40 * axis_score +
        0.15 * vertices_score)


def _square_score(features, config):
    if features["vertices"] != 4 or not features["convex"]:
        return 0.0
    edge_score = _ratio_score(
        features["edge_ratio"], 1.0, config["polygon_max_edge_ratio"])
    angle_score = _ratio_score(
        features["max_angle_cosine"], 0.0,
        config["square_max_angle_cosine"])
    rect_score = _clamp01(
        (features["rect_axis_ratio"] - config["square_min_rect_ratio"]) /
        (1.0 - config["square_min_rect_ratio"]))
    min_fill = config["square_min_fill_ratio"]
    fill_score = _clamp01(
        (features["rect_fill_ratio"] - min_fill) / (1.0 - min_fill))
    return float(
        0.30 * edge_score + 0.30 * angle_score +
        0.20 * rect_score + 0.20 * fill_score)


def _triangle_score(features, config):
    if features["vertices"] != 3 or not features["convex"]:
        return 0.0
    edge_score = _ratio_score(
        features["edge_ratio"], 1.0, config["polygon_max_edge_ratio"])
    angles = features["interior_angles_deg"]
    if any(angle < config["triangle_min_angle_deg"] or
           angle > config["triangle_max_angle_deg"] for angle in angles):
        return 0.0
    angle_error = sum(abs(angle - 60.0) for angle in angles) / len(angles)
    angle_span = max(
        60.0 - config["triangle_min_angle_deg"],
        config["triangle_max_angle_deg"] - 60.0)
    angle_score = _clamp01(1.0 - angle_error / angle_span)
    return float(0.55 * edge_score + 0.45 * angle_score)


def _contour_features(contour, approximation):
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    vertices = approximation.reshape(-1, 2).astype(np.float32)
    convex = bool(cv2.isContourConvex(approximation))
    circularity = 0.0
    if perimeter > 1e-6:
        circularity = float(4.0 * math.pi * area / (perimeter * perimeter))

    rotated_rect = cv2.minAreaRect(contour)
    rect_width = float(rotated_rect[1][0])
    rect_height = float(rotated_rect[1][1])
    rect_long = max(rect_width, rect_height)
    rect_short = min(rect_width, rect_height)
    rect_axis_ratio = rect_short / rect_long if rect_long > 1e-6 else 0.0
    rect_area = rect_width * rect_height
    rect_fill_ratio = area / rect_area if rect_area > 1e-6 else 0.0

    ellipse_axis_ratio = 0.0
    ellipse_diameter = 0.0
    if len(contour) >= 5:
        ellipse = cv2.fitEllipse(contour)
        axes = ellipse[1]
        long_axis = max(float(axes[0]), float(axes[1]))
        short_axis = min(float(axes[0]), float(axes[1]))
        if long_axis > 1e-6:
            ellipse_axis_ratio = short_axis / long_axis
            ellipse_diameter = (short_axis + long_axis) / 2.0

    lengths = edge_lengths(vertices) if len(vertices) >= 3 else []
    edge_ratio = (max(lengths) / min(lengths)
                  if lengths and min(lengths) > 1e-6 else 999.0)
    cosines = angle_cosines(vertices) if len(vertices) >= 3 else [1.0]
    angles = interior_angles_deg(vertices) if len(vertices) >= 3 else []
    return {
        "area_px": area,
        "perimeter_px": perimeter,
        "vertices": int(len(vertices)),
        "convex": convex,
        "circularity": circularity,
        "ellipse_axis_ratio": ellipse_axis_ratio,
        "ellipse_diameter_px": ellipse_diameter,
        "rect_axis_ratio": rect_axis_ratio,
        "rect_fill_ratio": rect_fill_ratio,
        "edge_ratio": float(edge_ratio),
        "edge_lengths_px": [float(value) for value in lengths],
        "max_angle_cosine": float(max(cosines)),
        "interior_angles_deg": [float(value) for value in angles],
    }


def _shape_size_px(shape_name, features):
    if shape_name == "circle":
        area_diameter = 2.0 * math.sqrt(features["area_px"] / math.pi)
        ellipse_diameter = features["ellipse_diameter_px"]
        if ellipse_diameter > 0:
            return float((area_diameter + ellipse_diameter) / 2.0)
        return float(area_diameter)
    lengths = features["edge_lengths_px"]
    return float(sum(lengths) / len(lengths)) if lengths else None


def detect_basic_shape(rectified_image, vision_config):
    """识别矫正目标纸中央的基本黑色实心图形。"""
    if rectified_image is None or len(rectified_image.shape) < 2:
        return {
            "ok": False,
            "status": "rectification_failed",
            "message": "Rectified image is invalid",
            "debug": {},
        }
    if len(rectified_image.shape) == 2:
        gray = rectified_image.copy()
    else:
        gray = cv2.cvtColor(rectified_image, cv2.COLOR_BGR2GRAY)
    preprocess = vision_config["preprocess"]
    blur_size = preprocess["blur_kernel"]
    blurred = cv2.GaussianBlur(gray, (blur_size, blur_size), 0)
    _threshold, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel_size = preprocess["morph_kernel"]
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    height, width = binary.shape[:2]
    shape_config = vision_config["shape"]
    border = max(2, int(round(
        min(width, height) * shape_config["border_margin_ratio"])))
    binary[:border, :] = 0
    binary[height - border:, :] = 0
    binary[:, :border] = 0
    binary[:, width - border:] = 0

    contours, _hierarchy = find_contours(binary, cv2.RETR_EXTERNAL)
    image_area = float(width * height)
    image_center = np.array([width / 2.0, height / 2.0], dtype=np.float32)
    image_diagonal = float(np.hypot(width, height))
    candidates = []
    debug_image = rectified_image.copy()

    for contour in contours:
        area = float(cv2.contourArea(contour))
        area_ratio = area / image_area
        if not (shape_config["min_area_ratio"] <= area_ratio <=
                shape_config["max_area_ratio"]):
            continue
        center = contour_center(contour)
        if center is None:
            continue
        center_offset_ratio = float(
            np.linalg.norm(center - image_center) / image_diagonal)
        if center_offset_ratio > shape_config["max_center_offset_ratio"]:
            continue
        x, y, contour_width, contour_height = cv2.boundingRect(contour)
        if (x <= border or y <= border or x + contour_width >= width - border or
                y + contour_height >= height - border):
            continue

        perimeter = float(cv2.arcLength(contour, True))
        approximation = cv2.approxPolyDP(
            contour, shape_config["approx_epsilon_ratio"] * perimeter, True)
        features = _contour_features(contour, approximation)
        scores = {
            "triangle": _triangle_score(features, shape_config),
            "square": _square_score(features, shape_config),
            "circle": _circle_score(features, shape_config),
        }
        shape_name = max(
            ("triangle", "square", "circle"),
            key=lambda name: scores[name])
        confidence = float(scores[shape_name])
        candidates.append({
            "contour": contour,
            "vertices_array": approximation.reshape(-1, 2),
            "center": center,
            "shape": shape_name,
            "confidence": confidence,
            "scores": scores,
            "features": features,
            "area_ratio": area_ratio,
            "center_offset_ratio": center_offset_ratio,
        })
        cv2.drawContours(debug_image, [contour], -1, (0, 165, 255), 2)

    debug = {
        "shape_binary": binary,
        "shape_contours": debug_image,
    }
    if not candidates:
        return {
            "ok": False,
            "status": "shape_not_found",
            "message": "No centered basic shape candidate",
            "candidates": [],
            "debug": debug,
        }

    candidates.sort(
        key=lambda item: (item["confidence"], item["area_ratio"]),
        reverse=True)
    best = candidates[0]
    if best["confidence"] < shape_config["min_confidence"]:
        status = "shape_unknown"
        message = "Shape candidate does not satisfy geometric rules"
        ok = False
    elif (len(candidates) > 1 and
          candidates[1]["confidence"] >= shape_config["min_confidence"] and
          best["confidence"] - candidates[1]["confidence"] <
          shape_config["ambiguity_margin"]):
        status = "shape_ambiguous"
        message = "Multiple high-quality shape candidates"
        ok = False
    else:
        status = "ok"
        message = ""
        ok = True

    return {
        "ok": ok,
        "status": status,
        "message": message,
        "shape": best["shape"] if ok else None,
        "confidence": best["confidence"],
        "contour": best["contour"],
        "vertices_array": best["vertices_array"],
        "center": best["center"],
        "size_px": _shape_size_px(best["shape"], best["features"]),
        "scores": best["scores"],
        "features": best["features"],
        "candidates": candidates,
        "debug": debug,
    }
