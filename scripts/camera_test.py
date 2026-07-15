"""Nano 摄像头采集单项测试。"""

import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
