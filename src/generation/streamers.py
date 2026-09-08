"""
Bộ truyền tải văn bản thời gian thực (Streaming Text Display).
Hỗ trợ cả Console Output (CLI) và Iterator Output (cho Web API / FastAPI / Gradio).
"""

import queue
import sys
import threading
import time
from abc import ABC, abstractmethod
from typing import Iterator, Optional


class BaseStreamer(ABC):
    """Lớp trừu tượng định nghĩa hợp đồng truyền tải văn bản theo luồng (Streaming)."""

    def on_prompt(self, text: str) -> None:
        """Được gọi một lần khi bắt đầu sinh văn bản với prompt ban đầu."""
        pass

    @abstractmethod
    def on_token(self, token_str: str) -> None:
        """Được gọi mỗi khi một token/ký tự mới được sinh ra."""
        pass

    def on_finish(self) -> None:
        """Được gọi khi hoàn thành toàn bộ quá trình sinh văn bản."""
        pass


class ConsoleStreamer(BaseStreamer):
    """Truyền trực tiếp từng ký tự/token ra console với hiệu ứng đánh máy."""

    def __init__(self, delay: float = 0.01) -> None:
        self.delay = delay

    def on_prompt(self, text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    def on_token(self, token_str: str) -> None:
        sys.stdout.write(token_str)
        sys.stdout.flush()
        if self.delay > 0:
            time.sleep(self.delay)

    def on_finish(self) -> None:
        sys.stdout.write("\n\n")
        sys.stdout.flush()


class TextIteratorStreamer(BaseStreamer):
    """
    Streamer dạng Iterator / Generator theo chuẩn Hugging Face.
    Cho phép lặp qua từng token thời gian thực, sẵn sàng cắm vào
    StreamingResponse của FastAPI hoặc yield trong Gradio / Streamlit.
    """

    def __init__(self, timeout: Optional[float] = None) -> None:
        self.text_queue: queue.Queue[Optional[str]] = queue.Queue()
        self.stop_signal = None
        self.timeout = timeout
        self._finished = threading.Event()
        self._finish_lock = threading.Lock()

    def on_prompt(self, text: str) -> None:
        # Tùy chọn bỏ qua hoặc đẩy prompt vào queue nếu cần
        pass

    def on_token(self, token_str: str) -> None:
        if self._finished.is_set():
            return
        self.text_queue.put(token_str)

    def on_finish(self) -> None:
        with self._finish_lock:
            if self._finished.is_set():
                return
            self._finished.set()
            self.text_queue.put(self.stop_signal)

    def cancel(self) -> None:
        """Wake a waiting iterator and ignore any later tokens."""
        self.on_finish()

    def __iter__(self) -> Iterator[str]:
        return self

    def __next__(self) -> str:
        while True:
            try:
                value = self.text_queue.get(timeout=self.timeout)
            except queue.Empty:
                # timeout is a polling interval, not a terminal stream failure.
                if self._finished.is_set():
                    raise StopIteration
                continue
            if value is None:
                raise StopIteration
            return value


__all__ = ["BaseStreamer", "ConsoleStreamer", "TextIteratorStreamer"]
