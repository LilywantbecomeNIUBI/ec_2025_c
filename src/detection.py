"""单帧处理入口。

阶段 2A 只验证帧是否有效，不把预览帧冒充目标测量结果。
"""

from src.result import create_result


def process_frame(frame, timestamp=None):
    """校验摄像头帧并返回统一结果。

    A4 目标纸和几何图形检测将在后续静态图像阶段实现。
    """
    if frame is None:
        return create_result(
            ok=False,
            status="invalid_frame",
            message="Frame is None",
            timestamp=timestamp)

    shape = getattr(frame, "shape", None)
    if shape is None or len(shape) < 2:
        return create_result(
            ok=False,
            status="invalid_frame",
            message="Frame has no valid image shape",
            timestamp=timestamp)

    height = int(shape[0])
    width = int(shape[1])
    if width <= 0 or height <= 0:
        return create_result(
            ok=False,
            status="invalid_frame",
            message="Frame dimensions must be positive",
            timestamp=timestamp)

    channels = int(shape[2]) if len(shape) >= 3 else 1
    return create_result(
        ok=True,
        status="frame_ready",
        message="Frame acquired; target measurement is not implemented yet",
        timestamp=timestamp,
        debug={
            "frame_shape": [height, width, channels],
            "frame_center_px": [width / 2.0, height / 2.0],
        })
