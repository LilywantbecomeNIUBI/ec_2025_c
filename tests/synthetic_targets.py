"""阶段 3 自动化测试使用的合成 A4 目标。"""

import math

import cv2
import numpy as np


def create_target_scene(shape_name, frame_size=(640, 480)):
    """生成带透视变化的黑框 A4 场景和理论内框角点。"""
    frame_width, frame_height = frame_size
    board_width = 300
    board_height = int(round(board_width * 297.0 / 210.0))
    border = int(round(board_width * 20.0 / 210.0))
    board = np.zeros((board_height, board_width, 3), dtype=np.uint8)
    cv2.rectangle(
        board, (border, border),
        (board_width - 1 - border, board_height - 1 - border),
        (255, 255, 255), -1)

    inner_left = border
    inner_top = border
    inner_right = board_width - 1 - border
    inner_bottom = board_height - 1 - border
    inner_width = inner_right - inner_left
    inner_height = inner_bottom - inner_top
    center_x = int(round((inner_left + inner_right) / 2.0))
    center_y = int(round((inner_top + inner_bottom) / 2.0))
    size = int(round(inner_width * 0.68))

    if shape_name == "circle":
        cv2.circle(board, (center_x, center_y), size // 2, (0, 0, 0), -1)
    elif shape_name == "square":
        half = size // 2
        cv2.rectangle(
            board, (center_x - half, center_y - half),
            (center_x + half, center_y + half), (0, 0, 0), -1)
    elif shape_name == "triangle":
        triangle_height = int(round(size * math.sqrt(3.0) / 2.0))
        points = np.array([
            [center_x, center_y - int(round(2.0 * triangle_height / 3.0))],
            [center_x - size // 2,
             center_y + int(round(triangle_height / 3.0))],
            [center_x + size // 2,
             center_y + int(round(triangle_height / 3.0))],
        ], dtype=np.int32)
        cv2.fillConvexPoly(board, points, (0, 0, 0))
    elif shape_name == "rectangle":
        half_width = size // 2
        half_height = size // 4
        cv2.rectangle(
            board, (center_x - half_width, center_y - half_height),
            (center_x + half_width, center_y + half_height), (0, 0, 0), -1)
    else:
        raise ValueError("Unknown synthetic shape: {}".format(shape_name))

    source = np.array([
        [0.0, 0.0],
        [board_width - 1.0, 0.0],
        [board_width - 1.0, board_height - 1.0],
        [0.0, board_height - 1.0],
    ], dtype=np.float32)
    destination = np.array([
        [175.0, 28.0],
        [458.0, 48.0],
        [438.0, 456.0],
        [153.0, 427.0],
    ], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(
        board, transform, (frame_width, frame_height),
        flags=cv2.INTER_LINEAR, borderValue=(180, 180, 180))
    mask = cv2.warpPerspective(
        np.full((board_height, board_width), 255, dtype=np.uint8),
        transform, (frame_width, frame_height),
        flags=cv2.INTER_NEAREST, borderValue=0)
    frame = np.full((frame_height, frame_width, 3), 180, dtype=np.uint8)
    frame[mask > 0] = warped[mask > 0]

    inner_corners = np.array([
        [inner_left, inner_top],
        [inner_right, inner_top],
        [inner_right, inner_bottom],
        [inner_left, inner_bottom],
    ], dtype=np.float32).reshape(1, 4, 2)
    expected_corners = cv2.perspectiveTransform(
        inner_corners, transform).reshape(4, 2)
    return frame, expected_corners
