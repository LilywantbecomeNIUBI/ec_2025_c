# 2025 年电赛 C 题复现

本项目用于在 NVIDIA Jetson Nano 上复现 2025 年全国大学生电子设计竞赛 C 题。

## 目录说明

- `main.py`：主程序入口
- `config.py`：摄像头参数、识别阈值和尺寸参数
- `src/camera.py`：摄像头采集
- `src/detection.py`：目标识别
- `src/measurement.py`：距离、尺寸等测量
- `src/calibration.py`：相机标定
- `src/visualization.py`：结果可视化
- `scripts/`：单项功能测试脚本
- `assets/`：测试图片与标定数据
- `outputs/`：程序运行结果
- `docs/`：题目分析与方案文档
- `models/`：模型文件的本地存放目录
- `tests/`：自动化测试

Windows 与 Jetson Nano 的依赖分别记录在 `requirements-windows.txt` 和
`requirements-nano.txt` 中。

