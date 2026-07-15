"""检测结果可视化。"""

import cv2
import numpy as np


def _draw_cross(image, point, color, size=8, thickness=2):
    x = int(round(point[0]))
    y = int(round(point[1]))
    cv2.line(image, (x - size, y), (x + size, y), color, thickness)
    cv2.line(image, (x, y - size), (x, y + size), color, thickness)


def draw_detection_overlay(frame, result):
    """在原图上绘制目标纸四角、中心偏差和状态。"""
    overlay = frame.copy()
    corners = result.get("board_corners_px") or []
    if len(corners) == 4:
        polygon = np.round(np.asarray(corners)).astype(np.int32)
        cv2.polylines(overlay, [polygon], True, (0, 255, 0), 2)
        for index, corner in enumerate(polygon):
            cv2.circle(overlay, tuple(corner), 4, (0, 255, 255), -1)
            cv2.putText(
                overlay, str(index), tuple(corner + np.array([5, -5])),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1,
                cv2.LINE_AA)

    height, width = overlay.shape[:2]
    frame_center = (width / 2.0, height / 2.0)
    _draw_cross(overlay, frame_center, (255, 0, 0), size=7)
    target_center = result.get("center_px")
    if target_center is not None:
        _draw_cross(overlay, target_center, (0, 0, 255), size=9)
        cv2.line(
            overlay,
            (int(round(frame_center[0])), int(round(frame_center[1]))),
            (int(round(target_center[0])), int(round(target_center[1]))),
            (255, 255, 0), 1)

    status = result.get("status", "unknown")
    shape = result.get("shape") or "-"
    confidence = result.get("shape_confidence")
    label = "status={} shape={}".format(status, shape)
    if confidence is not None:
        label += " confidence={:.2f}".format(confidence)
    cv2.rectangle(overlay, (0, 0), (width, 30), (0, 0, 0), -1)
    cv2.putText(
        overlay, label, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
        (255, 255, 255), 1, cv2.LINE_AA)
    return overlay


def draw_shape_overlay(rectified, shape_result):
    """在矫正图上绘制形状轮廓、顶点和中心。"""
    overlay = rectified.copy()
    contour = shape_result.get("contour")
    if contour is not None:
        cv2.drawContours(overlay, [contour], -1, (0, 255, 0), 2)
    vertices = shape_result.get("vertices_array")
    if vertices is not None:
        for vertex in np.asarray(vertices).reshape(-1, 2):
            cv2.circle(
                overlay, tuple(np.round(vertex).astype(np.int32)),
                5, (0, 0, 255), -1)
    center = shape_result.get("center")
    if center is not None:
        _draw_cross(overlay, center, (255, 0, 0), size=10)
    label = "{} {:.2f}".format(
        shape_result.get("shape") or shape_result.get("status", "unknown"),
        float(shape_result.get("confidence", 0.0)))
    cv2.putText(
        overlay, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
        (0, 0, 255), 2, cv2.LINE_AA)
    return overlay
