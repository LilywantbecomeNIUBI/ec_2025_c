"""项目集中配置。"""

import copy


DEFAULT_CAMERA_CONFIG = {
    "device": 0,
    "width": 640,
    "height": 480,
    "fps": 30,
    "warmup_frames": 30,
    "warmup_delay_s": 0.01,
    "read_failure_limit": 3,
    "reconnect_attempts": 3,
    "reconnect_delay_s": 0.5,
}


DEFAULT_VISION_CONFIG = {
    "preprocess": {
        "blur_kernel": 5,
        "morph_kernel": 3,
        "adaptive_block_size": 31,
        "adaptive_c": 5.0,
        "canny_low": 50,
        "canny_high": 150,
    },
    "board": {
        "inner_width_mm": 170.0,
        "inner_height_mm": 257.0,
        "pixel_per_mm": 3.0,
        "min_area_ratio": 0.03,
        "max_area_ratio": 0.90,
        "aspect_ratio_min": 1.30,
        "aspect_ratio_max": 1.75,
        "max_angle_cosine": 0.35,
        "min_border_contrast": 12.0,
        "border_ring_ratio": 0.04,
        "min_fill_ratio": 0.72,
        "edge_margin_px": 3,
        "approx_epsilon_ratio": 0.02,
        "subpixel_window_px": 5,
        "max_subpixel_shift_px": 8.0,
        "duplicate_corner_distance_px": 10.0,
        "ambiguity_score_margin": 0.04,
    },
    "shape": {
        "min_area_ratio": 0.05,
        "max_area_ratio": 0.70,
        "max_center_offset_ratio": 0.28,
        "border_margin_ratio": 0.02,
        "approx_epsilon_ratio": 0.02,
        "min_confidence": 0.65,
        "ambiguity_margin": 0.08,
        "circle_min_circularity": 0.78,
        "circle_min_axis_ratio": 0.82,
        "polygon_max_edge_ratio": 1.20,
        "square_max_angle_cosine": 0.25,
        "square_min_rect_ratio": 0.80,
        "square_min_fill_ratio": 0.70,
        "triangle_min_angle_deg": 48.0,
        "triangle_max_angle_deg": 72.0,
    },
}


def get_camera_config(overrides=None):
    """返回经过校验的摄像头配置副本。

    Args:
        overrides: 可选字典，只覆盖本次运行需要调整的项目。
    """
    config = dict(DEFAULT_CAMERA_CONFIG)
    if overrides:
        unknown_keys = sorted(set(overrides) - set(config))
        if unknown_keys:
            raise ValueError("Unknown camera config keys: {}".format(
                ", ".join(unknown_keys)))
        config.update(overrides)

    device = config["device"]
    if isinstance(device, bool) or not isinstance(device, (int, str)):
        raise ValueError("camera device must be a non-negative integer or path")
    if isinstance(device, int) and device < 0:
        raise ValueError("camera device index must be non-negative")
    if isinstance(device, str) and not device.strip():
        raise ValueError("camera device path must not be empty")

    positive_integer_keys = (
        "width",
        "height",
        "fps",
        "read_failure_limit",
        "reconnect_attempts",
    )
    for key in positive_integer_keys:
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("{} must be a positive integer".format(key))

    warmup_frames = config["warmup_frames"]
    if (isinstance(warmup_frames, bool) or
            not isinstance(warmup_frames, int) or warmup_frames < 0):
        raise ValueError("warmup_frames must be a non-negative integer")

    for key in ("warmup_delay_s", "reconnect_delay_s"):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError("{} must be a non-negative number".format(key))

    return config


def _merge_known_config(target, overrides, prefix=""):
    for key, value in overrides.items():
        path = "{}.{}".format(prefix, key) if prefix else key
        if key not in target:
            raise ValueError("Unknown vision config key: {}".format(path))
        if isinstance(target[key], dict):
            if not isinstance(value, dict):
                raise ValueError("{} must be a dictionary".format(path))
            _merge_known_config(target[key], value, path)
        else:
            target[key] = value


def get_vision_config(overrides=None):
    """返回经过基本校验的视觉配置深拷贝。"""
    config = copy.deepcopy(DEFAULT_VISION_CONFIG)
    if overrides:
        if not isinstance(overrides, dict):
            raise ValueError("vision config overrides must be a dictionary")
        _merge_known_config(config, overrides)

    preprocess = config["preprocess"]
    for key in ("blur_kernel", "morph_kernel", "adaptive_block_size"):
        value = preprocess[key]
        if (isinstance(value, bool) or not isinstance(value, int) or
                value <= 0 or value % 2 == 0):
            raise ValueError("{} must be a positive odd integer".format(key))
    if not 0 <= preprocess["canny_low"] < preprocess["canny_high"]:
        raise ValueError("invalid Canny threshold range")

    board = config["board"]
    for key in ("inner_width_mm", "inner_height_mm", "pixel_per_mm"):
        if float(board[key]) <= 0:
            raise ValueError("board.{} must be positive".format(key))
    if not 0 < board["min_area_ratio"] < board["max_area_ratio"] <= 1:
        raise ValueError("invalid board area ratio range")
    if not 1 < board["aspect_ratio_min"] < board["aspect_ratio_max"]:
        raise ValueError("invalid board aspect ratio range")

    shape = config["shape"]
    if not 0 < shape["min_area_ratio"] < shape["max_area_ratio"] <= 1:
        raise ValueError("invalid shape area ratio range")
    if not 0 <= shape["min_confidence"] <= 1:
        raise ValueError("shape.min_confidence must be between 0 and 1")
    return config
