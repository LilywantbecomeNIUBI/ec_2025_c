# 项目开发约定

本项目用于在 NVIDIA Jetson Nano 4GB 上复现 2025 年全国大学生电子设计竞赛 C 题。

开发、修改或审查本项目代码前，必须先阅读并遵守根目录下的
`AGENTS_Jetson_Nano.md`。尤其注意：

- Nano 端使用 Python 3.6，代码必须保持兼容。
- Windows 与 Nano 的依赖分开维护。
- 不得随意升级或覆盖 JetPack 自带的 OpenCV、NumPy、CUDA 和 TensorRT。
- 摄像头、CUDA、TensorRT、GPIO 相关功能必须在 Nano 实机上验证。
- 生成文件写入 `outputs/`，不要把大模型、引擎或临时图片提交到 Git。

