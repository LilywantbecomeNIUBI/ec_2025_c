"""项目集中配置。

当前阶段只放置已经实际使用的摄像头参数。后续视觉阈值将在对应功能
实现时再加入，避免先写入未经实测的“魔法数字”。
"""


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
