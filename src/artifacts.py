"""检测调试图片和 JSON 结果的统一保存功能。"""

import json
import os

import cv2


ARTIFACT_FILENAMES = {
    "original": "original.jpg",
    "gray": "gray.jpg",
    "binary": "binary.jpg",
    "edges": "edges.jpg",
    "board_candidates": "board_candidates.jpg",
    "board_corners": "board_corners.jpg",
    "rectified": "rectified.jpg",
    "shape_binary": "shape_binary.jpg",
    "shape_contours": "shape_contours.jpg",
    "final_overlay": "final_overlay.jpg",
}


def write_image(path, image):
    """兼容 Windows 中文路径的图片保存。"""
    extension = os.path.splitext(path)[1] or ".jpg"
    ok, encoded = cv2.imencode(extension, image)
    if not ok:
        raise IOError("Cannot encode image: {}".format(path))
    encoded.tofile(path)


def save_detection_artifacts(output_dir, result, artifacts):
    """保存当前检测的全部可用调试图片和 ``result.json``。"""
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    saved_files = []
    for name, filename in ARTIFACT_FILENAMES.items():
        artifact = artifacts.get(name)
        if artifact is None:
            continue
        path = os.path.join(output_dir, filename)
        write_image(path, artifact)
        saved_files.append(path)

    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as result_file:
        json.dump(result, result_file, ensure_ascii=False, indent=2,
                  sort_keys=True)
        result_file.write("\n")
    saved_files.append(result_path)
    return saved_files
