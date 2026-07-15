# 2025 年电赛 C 题复现

本项目用于在 NVIDIA Jetson Nano 上复现 2025 年全国大学生电子设计竞赛 C 题。

## 目录说明

- `main.py`：主程序入口
- `config.py`：摄像头参数、识别阈值和尺寸参数
- `src/camera.py`：摄像头采集
- `src/board_detector.py`：A4 黑框内侧四角检测
- `src/geometry.py`：角点排序和透视变换
- `src/shape_detector.py`：圆形、正方形和等边三角形识别
- `src/detection.py`：组合单帧检测流程
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

当前已建立摄像头基础链路、静态原图采集、A4 黑框内侧四角检测、透视
矫正、三种基本形状分类，以及 Nano 本地计算的浏览器 MJPEG 实时预览。
当前尚未实现相机标定、距离 `D`、实际尺寸 `x` 和多帧稳定测量，因此这些
字段仍返回 `null`。

## Windows 无硬件测试

首次创建独立 Windows 开发环境并安装 Windows 专用依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-windows.txt
python -m unittest discover -s tests -v
```

## Jetson Nano 摄像头测试

使用 JetPack 自带的 Python 3、OpenCV 和 NumPy，不要安装
`opencv-python`，也不要升级系统 NumPy：

```bash
cd /home/liwei/projects/EC_2025_C
source .venv/bin/activate
python3 scripts/camera_test.py --frames 3
```

程序默认打开 `/dev/video0` 对应的设备索引 `0`，请求 `640x480 @ 30 FPS`，
丢弃 30 帧后对三帧图像执行目标检测。也可以显式指定设备编号；推荐传整数
`0`，避免旧版 OpenCV 把 `/dev/video0` 字符串优先交给 GStreamer：

```bash
python3 scripts/camera_test.py --device 0 --frames 3
```

此命令需要 Nano、USB 摄像头和实机 OpenCV；不会修改系统环境，也不会保存
视频或图片。若打开失败，可先检查：

```bash
ls -l /dev/video0
v4l2-ctl --device=/dev/video0 --list-formats-ext
python3 -c "import cv2; print(cv2.__version__)"
```

## Nano 静态目标图片采集

以下命令预热摄像头，等待 2 秒后保存一张原始图片，并把元数据追加到
`captures.jsonl`。所有文件均写入已被 Git 忽略的 `outputs/`：

```bash
python3 scripts/capture_target_image.py \
  --shape circle \
  --size-cm 13 \
  --distance-cm 150 \
  --count 1
```

## 静态图片检测

```bash
python3 scripts/detection_test.py \
  --input outputs/static_targets/<IMAGE_NAME>.jpg \
  --output outputs/detection_result
```

输出目录包括原图、灰度图、二值图、边缘图、候选四边形、目标纸角点、透视矫正图、
形状轮廓、最终标注图和 `result.json`。成功退出码为 `0`；检测失败会保留
可用调试图并返回退出码 `2`。当前参数只通过合成图像测试，必须使用实际
目标纸图片继续调参后，才能评价识别率和误差。

## 浏览器实时调试预览

Nano 端运行：

```bash
cd /home/liwei/projects/EC_2025_C
source .venv/bin/activate
python3 main.py \
  --web \
  --device 0 \
  --host 0.0.0.0 \
  --port 8000 \
  --preview-fps 10
```

查询 Nano 局域网地址：

```bash
hostname -I
```

在同一局域网的 PC 浏览器访问：

```text
http://<NANO_IP>:8000
```

页面显示 Nano 生成的标注画面、检测状态、形状、置信度、`dx/dy`、单帧
处理耗时和预览 FPS。浏览器断开不会关闭摄像头；所有浏览器客户端共享同一
采集与检测线程，不会重复初始化 `/dev/video0`。

“保存当前完整调试快照”按钮只在点击时把当前帧及其灰度图、二值图、角点、
透视图、轮廓图和 JSON 写入：

```text
outputs/web_captures/<TIMESTAMP>_frame_<SEQUENCE>/
```

服务使用 Python 3.6 标准库 HTTP 和 OpenCV MJPEG，不需要安装 Flask。按
`Ctrl+C` 停止并释放摄像头。该页面没有身份认证，只应在比赛调试局域网中
使用，不应映射到公网。
