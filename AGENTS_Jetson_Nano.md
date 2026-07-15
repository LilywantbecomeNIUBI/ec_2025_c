# AGENTS.md — Jetson Nano 项目开发约束

> 本文档供 Codex 或其他代码助手读取。生成、修改或审查本项目代码时，必须以本文档记录的真实硬件和软件环境为准，不要默认使用现代桌面 Linux、x86_64 或新版 Python 环境。

## 1. 项目目标

本项目面向 **NVIDIA Jetson Nano 4GB**，主要用于：

- USB 摄像头图像采集
- OpenCV 图像处理
- CUDA 加速
- TensorRT 推理
- GPIO 外设控制
- 后续实时视觉或轻量级 AI 推理

开发采用 Windows 与 Jetson Nano 分离的双端工作流：

```text
Windows 最新版 VS Code + Codex
        ↓
代码编辑、Git、模型训练、非硬件逻辑测试
        ↓
GitHub
        ↓
Jetson Nano 拉取代码
        ↓
CUDA、摄像头、GPIO、TensorRT 实机运行
```

## 2. 目标硬件

| 项目 | 实际配置 |
|---|---|
| 开发套件 | NVIDIA Jetson Nano 4GB |
| 开发套件型号 | P3450 |
| 计算模块 | P3448 microSD 版本 |
| 载板 | P3449 B01 |
| 启动介质 | 32GB microSD |
| GPU | NVIDIA Tegra X1，Compute Capability 5.3 |
| 内存 | 约 4GB |
| 当前功耗模式 | 5W |
| 当前供电 | Micro-USB，J48 跳线帽已拔掉 |
| 摄像头 | USB2.0 PC CAMERA，`/dev/video0` |

当前 USB 摄像头已验证支持：

```text
YUYV 4:2:2
640 × 480
30 FPS
```

摄像头启动时应先预热并丢弃若干帧，避免自动曝光尚未稳定导致首帧全白。

## 3. Nano 端系统环境

| 软件项 | 实际版本 |
|---|---|
| JetPack | 4.6.1 SD Card Image |
| Ubuntu | 18.04.6 LTS |
| L4T | R32.7.1 |
| Linux 内核 | 4.9.253-tegra |
| CPU 架构 | aarch64 |
| glibc | 2.27 |
| CUDA | 10.2.300 |
| Python 3 | 3.6.9 |
| 默认 `python` | Python 2.7.17 |
| pip3 | 9.0.1 |
| OpenCV | 4.1.1 |
| GStreamer | 1.14.5，OpenCV 构建中为 YES |
| NumPy | 1.13.3 |
| TensorRT Python 包 | 8.2.1.8 |
| Jetson.GPIO | 2.0.17 |

注意：TensorRT Python 包版本已经检测到，但完整 TensorRT 推理链路仍应在 Nano 实机上验证，包括 `import tensorrt`、`trtexec` 和最小推理示例。

## 4. 账户与目录

Nano 账户：

```text
用户名：liwei
主机名：liwei-desktop
```

Nano 项目目录：

```bash
/home/liwei/projects/nano_test
```

Windows 项目目录：

```text
E:\Nano\nano_test
```

GitHub 仓库：

```text
https://github.com/LilywantbecomeNIUBI/nano_test
```

Nano 端远程仓库使用 SSH：

```text
git@github.com:LilywantbecomeNIUBI/nano_test.git
```

## 5. Python 运行规则

### 5.1 必须显式使用 Python 3

Nano 的 `python` 默认指向 Python 2.7，因此命令必须写成：

```bash
python3 script.py
```

不要生成只写 `python script.py` 的运行说明。

### 5.2 Python 语法必须兼容 3.6

禁止使用 Python 3.7 及以上才支持的语法或标准库特性，包括但不限于：

- `dataclasses`
- `from __future__ import annotations`
- `list[str]`、`dict[str, int]` 等内置泛型写法
- `str | None` 联合类型
- `match ... case`
- 海象运算符 `:=`
- f-string 的调试语法 `f"{value=}"`
- `subprocess.run(..., capture_output=True, text=True)`
- 依赖较新 Python 才存在的标准库 API

兼容写法示例：

```python
from typing import Dict, List, Optional, Tuple

def open_camera(device_id=0):
    # type: (int) -> Optional[object]
    pass
```

普通 f-string 可以使用，因为 Python 3.6 支持。

### 5.3 虚拟环境

项目已有虚拟环境：

```bash
/home/liwei/projects/nano_test/.venv
```

创建方式：

```bash
python3 -m venv .venv --system-site-packages
```

运行项目前优先：

```bash
cd /home/liwei/projects/nano_test
source .venv/bin/activate
python3 script.py
```

必须保留 `--system-site-packages` 的设计，因为 OpenCV、NumPy、TensorRT 等组件来自 JetPack 系统环境。

## 6. 依赖管理原则

### 6.1 不得破坏 JetPack 配套环境

不要建议或自动执行下列操作：

```text
升级 Ubuntu
升级 glibc
升级 Linux 内核
升级系统 Python
替换 CUDA
重新安装 NVIDIA 驱动
使用非官方系统覆盖当前 JetPack
```

也不要为了满足单个 Python 包而强行升级整个系统。

### 6.2 禁止随意覆盖系统包

不要执行：

```bash
pip3 install --upgrade numpy
pip3 install opencv-python
pip3 install opencv-contrib-python
```

当前 OpenCV 4.1.1 和 NumPy 1.13.3 已经在 Nano 上验证可用，并与 JetPack 环境配套。

安装新依赖前，应先检查：

1. 是否支持 Python 3.6；
2. 是否支持 Linux aarch64；
3. 是否与 CUDA 10.2、JetPack 4.6.1 兼容；
4. 是否提供 Jetson 专用安装包；
5. 是否会覆盖系统自带 NumPy、OpenCV、TensorRT 或 CUDA。

### 6.3 `requirements-nano.txt` 的定位

`requirements-nano.txt` 主要用于记录 Nano 当前环境，不应默认在 Windows 或其他机器上完整执行：

```bash
pip install -r requirements-nano.txt
```

其中可能包含只适用于 Ubuntu、aarch64、JetPack 或 NVIDIA 驱动的包。

Windows 依赖和 Nano 依赖必须分开维护，例如：

```text
requirements-windows.txt
requirements-nano.txt
```

## 7. OpenCV 与摄像头代码要求

摄像头设备：

```text
/dev/video0
```

基础 OpenCV 打开方式可以使用：

```python
cap = cv2.VideoCapture(0)
```

代码必须包含：

- 检查 `cap.isOpened()`；
- 设置或确认分辨率与帧率；
- 启动后预热并丢弃前若干帧；
- 检查每次 `read()` 的返回值；
- 使用 `try/finally` 或等效结构释放摄像头；
- 无图形桌面环境时不要强依赖 `cv2.imshow()`；
- 实时循环中提供退出条件；
- 避免把整段视频无限保存到 32GB microSD。

推荐基础结构：

```python
import time
import cv2


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open /dev/video0")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    try:
        for _ in range(30):
            ok, _frame = cap.read()
            if not ok:
                raise RuntimeError("Camera warm-up failed")
            time.sleep(0.01)

        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError("Camera capture failed")

        print("Frame shape: {}".format(frame.shape))
    finally:
        cap.release()


if __name__ == "__main__":
    main()
```

已实测摄像头连续采集约 29.99 FPS，因此后续代码性能明显低于 30 FPS 时，应区分是模型推理耗时、图像预处理耗时，还是摄像头取流问题。

## 8. CUDA 代码要求

CUDA 已通过 `nvcc` 编译和内核运行测试：

```text
CUDA device count: 1
GPU: NVIDIA Tegra X1
Compute capability: 5.3
```

编译器路径：

```bash
/usr/local/cuda/bin/nvcc
```

生成 CUDA 代码时：

- 兼容 CUDA 10.2；
- 不使用较新 CUDA 才支持的 API；
- 默认目标架构应考虑 `sm_53`；
- 提供清晰的编译命令；
- 检查每个 CUDA API 返回值；
- 控制显存与统一内存占用；
- 避免为 4GB 内存设备分配过大缓冲区；
- 先提供小规模正确性测试，再做性能优化。

示例编译命令：

```bash
/usr/local/cuda/bin/nvcc -arch=sm_53 source.cu -o app
./app
```

## 9. TensorRT 代码要求

目标环境：

```text
TensorRT 8.2.1.8
CUDA 10.2
Python 3.6
aarch64
JetPack 4.6.1
```

生成 TensorRT 代码时：

- 不默认采用 TensorRT 9 或 10 的 API；
- 不生成仅适配 x86_64 的安装命令；
- 明确区分 ONNX 导出、Engine 构建和 Nano 推理；
- TensorRT Engine 与硬件、TensorRT 版本和精度配置相关，不应在任意电脑上构建后直接假设可在 Nano 使用；
- 优先在 Nano 上构建 Engine；
- 默认先支持 FP32，再根据实测决定 FP16；
- 不默认使用 INT8，除非提供校准数据与校准流程；
- 对动态输入尺寸、绑定索引和内存拷贝进行显式检查；
- 所有 TensorRT 示例必须标注“需 Nano 实机验证”。

## 10. GPIO 代码要求

GPIO 尚未完成完整实机验证。生成 GPIO 代码时：

- 使用 `Jetson.GPIO`，不要默认使用 Raspberry Pi 专用库；
- 明确引脚编号模式，如 `GPIO.BOARD` 或 `GPIO.BCM`；
- 不猜测实际接线；
- 在代码注释中提醒确认电压与引脚；
- 使用 `try/finally` 调用 `GPIO.cleanup()`；
- 禁止将 5V 直接接入仅支持 3.3V 的 GPIO；
- 涉及电机、继电器或大电流负载时，必须提醒使用驱动电路和独立供电。

## 11. 资源限制

Jetson Nano 的资源有限：

```text
内存约 4GB
microSD 约 32GB
当前 5W 模式
当前 Micro-USB 供电
```

因此代码设计应：

- 避免一次性加载大型模型；
- 避免无界队列和无限缓存；
- 避免高分辨率视频的长期落盘；
- 对线程和进程数量保持克制；
- 为摄像头处理使用固定长度队列；
- 必要时降低输入分辨率、批大小或推理频率；
- 记录 FPS、推理延迟和内存占用；
- 对电源不足、掉帧和温度问题保持警惕。

当前使用 Micro-USB 5V 3A 和 5W 模式。高负载 CUDA、摄像头、多 USB 外设或长时间推理时，可能需要改用稳定的 5V 4A 圆口电源，并在使用圆口供电时短接 J48。

## 12. Git 与双端同步规则

Windows 端通常负责写代码：

```powershell
git pull
git add .
git commit -m "Describe the change"
git push
```

Nano 端负责实机测试：

```bash
cd /home/liwei/projects/nano_test
git pull
source .venv/bin/activate
python3 script.py
```

Nano 端修改后：

```bash
git add .
git commit -m "Describe Nano-side change"
git push
```

然后 Windows 再执行：

```powershell
git pull
```

不要假设 Windows 与 Nano 共享同一个文件系统。代码传递依赖 GitHub。

## 13. VS Code 约束

Windows 最新版 VS Code：

- Codex
- 本地代码编辑
- Git 操作
- 文档编写
- 非硬件逻辑测试
- 模型训练或转换

VS Code 1.85.2 便携版：

- Remote-SSH 连接 Nano
- Nano 端终端
- 摄像头、CUDA、GPIO、TensorRT 实机测试

最新版 VS Code Remote Server 与 Nano 的 glibc 2.27、内核 4.9.253-tegra 不兼容。不要通过升级 glibc 或内核来解决该问题。

## 14. 已验证能力

以下链路已经实际验证成功：

- JetPack 4.6.1 正常启动；
- Python 3.6.9 正常运行；
- CUDA 10.2 可编译并执行内核；
- OpenCV 4.1.1 可导入；
- NumPy 1.13.3 可导入；
- OpenCV 图像生成与保存成功；
- USB 摄像头 `/dev/video0` 单帧采集成功；
- USB 摄像头 640×480 约 30 FPS 连续采集成功；
- `.venv --system-site-packages` 正常；
- SSH 正常；
- 旧版 VS Code Remote-SSH 正常；
- Windows → GitHub → Nano 同步工作流正常；
- TensorRT 8.2.1.8 Python 包可导入；
- `/usr/src/tensorrt/bin/trtexec` 可执行并报告 `TensorRT v8201`；
- Nano 本机可构建最小 FP32 TensorRT Engine；
- CUDA Runtime 内存传输、TensorRT GPU 推理及数值核对成功。

## 15. 尚需验证的能力

以下功能不能视为已经完成：

- ONNX 到 TensorRT Engine 的完整转换；
- Jetson.GPIO 实际引脚控制；
- Jetson 专用 PyTorch；
- 摄像头实时神经网络推理。

Codex 在涉及这些功能时，应提供分阶段测试代码，并明确指出需要在 Nano 上运行验证。

## 16. Codex 输出要求

每次生成代码时应尽量同时给出：

1. 代码运行位置：Windows 或 Nano；
2. 所需 Python/CUDA/TensorRT 版本；
3. 文件保存路径；
4. 完整运行命令；
5. 依赖安装方式；
6. 预期输出；
7. 常见错误与检查命令；
8. 是否需要摄像头、GPIO 或 GPU 实机；
9. 是否会修改系统环境；
10. 回滚方式。

代码应优先做到：

- Python 3.6 兼容；
- 清晰、可直接运行；
- 有异常处理；
- 有资源释放；
- 不隐藏关键配置；
- 不破坏 JetPack 系统依赖；
- 先正确，再优化。

## 17. 禁止事项速查

Codex 不得默认建议：

```text
升级到 Ubuntu 20.04/22.04
升级 glibc
升级内核
升级系统 Python
直接安装最新版 PyTorch
直接安装最新版 TensorRT
pip install opencv-python
随意升级 NumPy
将 x86_64 安装命令用于 Nano
使用 Python 3.7+ 专属语法
使用 CUDA 11/12 专属 API
忽略 4GB 内存与 32GB microSD 限制
```

## 18. 当前推荐的下一步

TensorRT Python、`trtexec`、本机 Engine 构建和最小 GPU 推理已经验证。下一步优先验证 ONNX 转换链路：

```text
1. 在 Windows 或兼容环境中构建一个极小 ONNX 模型
2. 将 ONNX 模型同步到 Nano
3. 在 Nano 上用 trtexec 转换为 TensorRT Engine
4. 运行单次推理并核对结果
5. 再接入 USB 摄像头实时推理
```

当前可以确认 TensorRT 基础运行环境配置成功；在 ONNX 转换验证完成前，不应把完整模型部署链路写成“已经完全验证”。
