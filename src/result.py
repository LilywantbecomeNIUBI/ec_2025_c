"""统一测量结果结构。"""

import time


def create_result(ok=False, status="not_processed", message="", timestamp=None,
                  debug=None):
    """创建字段稳定、可直接 JSON 序列化的结果字典。"""
    if timestamp is None:
        timestamp = time.time()
    return {
        "ok": bool(ok),
        "status": str(status),
        "message": str(message),
        "timestamp": float(timestamp),
        "shape": None,
        "shape_confidence": None,
        "distance_cm": None,
        "size_cm": None,
        "center_px": None,
        "dx_px": None,
        "dy_px": None,
        "board_corners_px": [],
        "quality": {
            "board_score": None,
            "shape_score": None,
            "reprojection_error_px": None,
            "distance_consistency_cm": None,
        },
        "debug": dict(debug or {}),
    }
