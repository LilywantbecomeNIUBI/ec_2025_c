"""USB 摄像头采集、预热、读取和重连。"""

import time

from config import get_camera_config


class CameraError(RuntimeError):
    """摄像头无法完成请求的操作。"""


class CameraReader(object):
    """对 OpenCV ``VideoCapture`` 的小型可靠性封装。

    ``capture_factory`` 仅用于无硬件测试。Nano 正常运行时不传该参数，
    OpenCV 会在第一次打开摄像头时延迟导入。
    """

    _FALLBACK_PROPERTY_IDS = {
        "width": 3,
        "height": 4,
        "fps": 5,
    }

    def __init__(self, config=None, capture_factory=None, sleep_fn=None,
                 clock_fn=None):
        self.config = get_camera_config(config)
        self._capture_factory = capture_factory
        self._sleep = sleep_fn or time.sleep
        self._clock = clock_fn or time.time
        self._capture = None
        self._cv2 = None
        self._consecutive_failures = 0
        self.last_error = ""

    @property
    def is_opened(self):
        """摄像头当前是否处于打开状态。"""
        return (self._capture is not None and
                bool(self._capture.isOpened()))

    def _load_cv2(self):
        if self._cv2 is None:
            try:
                import cv2
            except ImportError as exc:
                raise CameraError(
                    "OpenCV is unavailable. On Nano, use the JetPack system "
                    "OpenCV inside the --system-site-packages virtual environment."
                ) from exc
            self._cv2 = cv2
        return self._cv2

    def _create_capture(self):
        if self._capture_factory is not None:
            return self._capture_factory(self.config["device"])
        cv2 = self._load_cv2()
        return cv2.VideoCapture(self.config["device"])

    def _property_id(self, name):
        if self._cv2 is None:
            return self._FALLBACK_PROPERTY_IDS[name]
        attribute_names = {
            "width": "CAP_PROP_FRAME_WIDTH",
            "height": "CAP_PROP_FRAME_HEIGHT",
            "fps": "CAP_PROP_FPS",
        }
        return getattr(
            self._cv2,
            attribute_names[name],
            self._FALLBACK_PROPERTY_IDS[name])

    def _apply_requested_properties(self, capture):
        for name in ("width", "height", "fps"):
            capture.set(self._property_id(name), self.config[name])

    def open(self):
        """打开摄像头并请求配置的分辨率和帧率。"""
        self.release()
        try:
            capture = self._create_capture()
        except CameraError:
            raise
        except Exception as exc:
            self.last_error = "Cannot create camera capture: {}".format(exc)
            raise CameraError(self.last_error)

        if capture is None or not capture.isOpened():
            if capture is not None:
                capture.release()
            self.last_error = "Cannot open camera device {}".format(
                self.config["device"])
            raise CameraError(self.last_error)

        self._capture = capture
        self._apply_requested_properties(capture)
        self._consecutive_failures = 0
        self.last_error = ""
        return self.get_actual_settings()

    def get_actual_settings(self):
        """读取驱动实际接受的分辨率和帧率。"""
        if not self.is_opened:
            return {}
        return {
            "device": self.config["device"],
            "width": float(self._capture.get(self._property_id("width"))),
            "height": float(self._capture.get(self._property_id("height"))),
            "fps": float(self._capture.get(self._property_id("fps"))),
        }

    def _read_capture(self):
        try:
            ok, frame = self._capture.read()
        except Exception as exc:
            self.last_error = "Camera read raised an exception: {}".format(exc)
            return False, None
        if not ok or frame is None:
            self.last_error = "Camera returned an empty frame"
            return False, None
        return True, frame

    def read(self):
        """返回 ``(ok, frame, timestamp)``，连续失败时尝试重连。"""
        timestamp = self._clock()
        if not self.is_opened:
            self.last_error = "Camera is not open"
            return False, None, timestamp

        ok, frame = self._read_capture()
        if ok:
            self._consecutive_failures = 0
            self.last_error = ""
            return True, frame, timestamp

        self._consecutive_failures += 1
        if self._consecutive_failures < self.config["read_failure_limit"]:
            return False, None, timestamp

        if not self.reconnect():
            return False, None, timestamp

        timestamp = self._clock()
        ok, frame = self._read_capture()
        if ok:
            self._consecutive_failures = 0
            self.last_error = ""
            return True, frame, timestamp

        self._consecutive_failures = 1
        return False, None, timestamp

    def warmup(self, frame_count=None):
        """丢弃预热帧，并返回最后一帧。"""
        count = self.config["warmup_frames"] if frame_count is None else frame_count
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("frame_count must be a non-negative integer")
        if not self.is_opened:
            raise CameraError("Cannot warm up a camera that is not open")

        last_frame = None
        for index in range(count):
            ok, frame, _timestamp = self.read()
            if not ok:
                raise CameraError(
                    "Camera warm-up failed at frame {}/{}: {}".format(
                        index + 1, count, self.last_error))
            last_frame = frame
            if self.config["warmup_delay_s"] > 0:
                self._sleep(self.config["warmup_delay_s"])
        return last_frame

    def reconnect(self):
        """释放后按配置次数重试打开摄像头。"""
        attempts = self.config["reconnect_attempts"]
        delay_s = self.config["reconnect_delay_s"]
        last_error = self.last_error
        self.release()

        for attempt in range(attempts):
            if delay_s > 0:
                self._sleep(delay_s)
            try:
                self.open()
                return True
            except CameraError as exc:
                last_error = str(exc)
                if attempt + 1 == attempts:
                    break

        self.last_error = "Camera reconnect failed after {} attempts: {}".format(
            attempts, last_error)
        return False

    def release(self):
        """安全释放摄像头；可重复调用。"""
        capture = self._capture
        self._capture = None
        if capture is not None:
            capture.release()
        self._consecutive_failures = 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
        return False
