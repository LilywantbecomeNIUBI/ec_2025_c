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

## 当前实现状态

阶段 2A 已建立摄像头基础链路：集中配置、打开、参数请求、预热、逐帧读取、
连续失败重连、资源释放和统一帧结果。当前尚未实现 A4 目标纸、形状、距离、
尺寸和 Web 检测；`frame_ready` 只表示摄像头帧有效。

## Windows 无硬件测试

测试只使用 Python 标准库和模拟摄像头，不需要安装 OpenCV：

```powershell
python -m unittest discover -s tests -v
```

## Jetson Nano 摄像头测试

使用 JetPack 自带的 Python 3、OpenCV 和 NumPy，不要安装
`opencv-python`，也不要升级系统 NumPy：

```bash
cd /home/liwei/projects/nano_test
source .venv/bin/activate
python3 scripts/camera_test.py --frames 3
```

程序默认打开 `/dev/video0` 对应的设备索引 `0`，请求 `640x480 @ 30 FPS`，
丢弃 30 帧后输出三条 `frame_ready` JSON 结果。也可以显式指定设备：

```bash
python3 scripts/camera_test.py --device /dev/video0 --frames 3
```

此命令需要 Nano、USB 摄像头和实机 OpenCV；不会修改系统环境，也不会保存
视频或图片。若打开失败，可先检查：

```bash
ls -l /dev/video0
v4l2-ctl --device=/dev/video0 --list-formats-ext
python3 -c "import cv2; print(cv2.__version__)"
```
