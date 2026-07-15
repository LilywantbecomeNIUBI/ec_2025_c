"""目标纸和基本几何图形共用的二维几何函数。"""

import math

import cv2
import numpy as np


def order_corners(points):
    """将四角统一为左上、右上、右下、左下。"""
    array = np.asarray(points, dtype=np.float32).reshape(4, 2)
    ordered_by_y = array[np.argsort(array[:, 1])]
    top = ordered_by_y[:2]
    bottom = ordered_by_y[2:]
    top = top[np.argsort(top[:, 0])]
    bottom = bottom[np.argsort(bottom[:, 0])]
    return np.array(
        [top[0], top[1], bottom[1], bottom[0]], dtype=np.float32)


def edge_lengths(points):
    """返回闭合多边形的各边长度。"""
    array = np.asarray(points, dtype=np.float32).reshape(-1, 2)
    lengths = []
    for index in range(len(array)):
        next_index = (index + 1) % len(array)
        lengths.append(float(np.linalg.norm(array[index] - array[next_index])))
    return lengths


def angle_cosines(points):
    """返回每个内角的余弦绝对值。"""
    array = np.asarray(points, dtype=np.float32).reshape(-1, 2)
    cosines = []
    for index in range(len(array)):
        previous = array[index - 1] - array[index]
        following = array[(index + 1) % len(array)] - array[index]
        denominator = float(np.linalg.norm(previous) * np.linalg.norm(following))
        if denominator <= 1e-6:
            cosines.append(1.0)
        else:
            cosine = abs(float(np.dot(previous, following)) / denominator)
            cosines.append(min(1.0, cosine))
    return cosines


def interior_angles_deg(points):
    """返回多边形各内角，单位为度。"""
    return [math.degrees(math.acos(max(-1.0, min(1.0, value))))
            for value in angle_cosines(points)]


def contour_center(contour):
    """返回轮廓质心；退化轮廓返回 ``None``。"""
    moments = cv2.moments(contour)
    if abs(moments["m00"]) <= 1e-6:
        return None
    return np.array([
        moments["m10"] / moments["m00"],
        moments["m01"] / moments["m00"],
    ], dtype=np.float32)


def find_contours(binary, mode=cv2.RETR_LIST):
    """兼容 OpenCV 3/4 的 ``findContours`` 返回格式。"""
    found = cv2.findContours(binary, mode, cv2.CHAIN_APPROX_SIMPLE)
    if len(found) == 2:
        return found[0], found[1]
    return found[1], found[2]


def board_output_size(board_config):
    """根据内部矩形毫米尺寸和输出比例计算矫正图大小。"""
    width = int(round(
        board_config["inner_width_mm"] * board_config["pixel_per_mm"]))
    height = int(round(
        board_config["inner_height_mm"] * board_config["pixel_per_mm"]))
    return width, height


def rectify_board(frame, corners, board_config):
    """把目标纸内部白色矩形透视变换为竖直标准平面。"""
    ordered = order_corners(corners)
    width, height = board_output_size(board_config)
    destination = np.array([
        [0.0, 0.0],
        [width - 1.0, 0.0],
        [width - 1.0, height - 1.0],
        [0.0, height - 1.0],
    ], dtype=np.float32)
    homography = cv2.getPerspectiveTransform(ordered, destination)
    rectified = cv2.warpPerspective(frame, homography, (width, height))
    return rectified, homography


def map_point_to_source(point, homography):
    """将矫正图上的一个点映射回原图。"""
    inverse = np.linalg.inv(homography)
    source = cv2.perspectiveTransform(
        np.asarray(point, dtype=np.float32).reshape(1, 1, 2), inverse)
    return source.reshape(2)
