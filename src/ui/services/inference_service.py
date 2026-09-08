"""
Inference Service: Quản lý nạp mô hình, hoán đổi checkpoint và điều phối sinh văn bản theo luồng (Streaming).
"""

import json
import os
import threading
import time
from typing import Any, Dict, Iterator, List, Optional

import torch

from src.core.config import GenerationConfig, ModelConfig
from src.core.logging import get_logger
from src.data.tokenizers import BaseTokenizer, load_tokenizer
from src.generation import (
    BaseGenerator,
    GeneratorRegistry,
    TextIteratorStreamer,
    get_generator,
)
from src.models.base import BaseModel
from src.models.registry import ModelRegistry

logger = get_logger("InferenceService")


class InferenceService:
    """Service singleton phục vụ suy luận văn bản và quản lý checkpoints cho Web UI."""

    def __init__(
        self,
        checkpoint_dir: str = "checkpoints",
        default_checkpoint: str = "checkpoints/best_model.pt",
        vocab_path: str = "data/vocab.json",
        device: str = "auto",
        backend: str = "local",
    ) -> None:
        self.checkpoint_dir = checkpoint_dir
        self.current_checkpoint_path: Optional[str] = None
        self.vocab_path = vocab_path
        self.device_str = (
            "cuda"
            if (device == "auto" and torch.cuda.is_available())
            else ("cpu" if device == "auto" else device)
        )
        self.current_backend: str = backend
        self.tokenizer: Optional[BaseTokenizer] = None
        self.model: Optional[BaseModel] = None
        self.generator: Optional[BaseGenerator] = None
        self._lock = threading.Lock()

        # Nạp mặc định nếu checkpoint và từ vựng tồn tại
        if os.path.exists(vocab_path):
            try:
                self.tokenizer = load_tokenizer(vocab_path)
            except Exception as e:
                logger.warning(f"Chưa thể nạp tokenizer từ {vocab_path}: {e}")

        if os.path.exists(default_checkpoint):
            try:
                self.load_checkpoint(default_checkpoint)
            except Exception as e:
                logger.warning(f"Chưa thể nạp checkpoint mặc định {default_checkpoint}: {e}")

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """Quét và trả về danh sách tất cả checkpoint cùng metadata."""
        checkpoints: List[Dict[str, Any]] = []
        if not os.path.exists(self.checkpoint_dir):
            return checkpoints

        for fname in os.listdir(self.checkpoint_dir):
            if fname.endswith(".pt") or fname.endswith(".pth"):
                fpath = os.path.join(self.checkpoint_dir, fname)
                stat = os.stat(fpath)
                size_mb = round(stat.st_size / (1024 * 1024), 2)
                modified_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                is_active = os.path.abspath(fpath) == (
                    os.path.abspath(self.current_checkpoint_path)
                    if self.current_checkpoint_path
                    else ""
                )

                # Đọc nhanh metadata nếu có
                step = None
                val_loss = None
                run_name = None
                try:
                    meta = torch.load(fpath, map_location="cpu", weights_only=True)
                    if isinstance(meta, dict):
                        step = meta.get("step")
                        raw_val = meta.get("val_loss")
                        if raw_val is not None:
                            try:
                                v = float(raw_val)
                                import math

                                if not math.isnan(v) and not math.isinf(v) and v > 0:
                                    val_loss = round(v, 4)
                            except (ValueError, TypeError):
                                pass
                        run_name = meta.get("run_name")
                except Exception:
                    pass

                checkpoints.append(
                    {
                        "filename": fname,
                        "path": fpath.replace("\\", "/"),
                        "size_mb": size_mb,
                        "modified_time": modified_time,
                        "is_active": is_active,
                        "step": step,
                        "val_loss": val_loss,
                        "run_name": run_name,
                    }
                )

        # Xác định val_loss thấp nhất thực tế trên toàn bộ checkpoint
        valid_losses = [c["val_loss"] for c in checkpoints if c.get("val_loss") is not None]
        min_loss = min(valid_losses) if valid_losses else None

        for c in checkpoints:
            c["is_best_val"] = (
                min_loss is not None
                and c.get("val_loss") is not None
                and abs(c["val_loss"] - min_loss) < 1e-5
            )
            fname = c["filename"]
            if fname == "best_model.pt":
                c["tag"] = "best"
            elif fname == "last_model.pt":
                c["tag"] = "canonical_last"
            elif fname.endswith("_last.pt"):
                c["tag"] = "run_last"
            elif "_step" in fname:
                c["tag"] = "top_k"
            else:
                c["tag"] = "custom"

        def _checkpoint_sort_key(x: Dict[str, Any]):
            # best_model.pt luôn được ghim ở đầu bảng (ưu tiên 0 so với 1)
            is_best = 0 if x["filename"] == "best_model.pt" else 1
            mtime = 0.0
            try:
                mtime = time.mktime(time.strptime(x["modified_time"], "%Y-%m-%d %H:%M:%S"))
            except Exception:
                pass
            step = x.get("step") or 0
            # Sắp xếp: best lên trước, sau đó là thời gian mới nhất (mtime giảm dần), step giảm dần
            return (is_best, -mtime, -step)

        checkpoints.sort(key=_checkpoint_sort_key)
        return checkpoints

    def list_generators(self) -> List[str]:
        """Danh sách tất cả các generator backend đã đăng ký trong GeneratorRegistry."""
        return GeneratorRegistry.list_generators()

    def set_backend(self, backend: str) -> None:
        """Chuyển đổi generator backend sang một backend khác trong GeneratorRegistry."""
        with self._lock:
            backend_clean = backend.lower().strip()
            # Luôn xác thực tên backend, kể cả khi model/tokenizer chưa được nạp.
            # Nếu không, UI có thể lưu một backend không tồn tại và chỉ lỗi muộn
            # ở lần load checkpoint/generate tiếp theo.
            GeneratorRegistry.get(backend_clean)
            if self.model is not None and self.tokenizer is not None:
                self.generator = get_generator(
                    backend_clean,
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=self.device_str,
                )
            self.current_backend = backend_clean
            logger.info(f"Đã chuyển đổi Generator backend sang: '{backend_clean}'")

    def load_checkpoint(self, checkpoint_path: str, backend: Optional[str] = None) -> None:
        """Nạp checkpoint mới và chỉ commit state sau khi toàn bộ quá trình thành công."""
        with self._lock:
            target_backend = self.current_backend
            if backend:
                target_backend = backend.lower().strip()
            GeneratorRegistry.get(target_backend)

            if not os.path.exists(checkpoint_path):
                raise FileNotFoundError(f"Không tìm thấy file checkpoint: {checkpoint_path}")

            tokenizer = self.tokenizer
            if tokenizer is None and os.path.exists(self.vocab_path):
                tokenizer = load_tokenizer(self.vocab_path)

            checkpoint = torch.load(
                checkpoint_path, map_location=self.device_str, weights_only=True
            )
            cfg_dict = checkpoint.get("config", {}).get("model", {})
            model_config = ModelConfig.from_kwargs_safe(cfg_dict, ignore_unknown=True)
            model = ModelRegistry.create(model_config.name, model_config)

            if isinstance(model, torch.nn.Module):
                model.load_state_dict(checkpoint["model_state_dict"])
                model.to(self.device_str)
                model.eval()

            generator = get_generator(
                target_backend,
                model=model,
                tokenizer=tokenizer,
                device=self.device_str,
            )

            # Atomic state commit: failed validation/load above must leave the active service untouched.
            self.tokenizer = tokenizer
            self.model = model
            self.generator = generator
            self.current_backend = target_backend
            self.current_checkpoint_path = checkpoint_path
            logger.info(
                f"Đã nạp checkpoint thành công: {checkpoint_path} trên {self.device_str} (Backend: '{self.current_backend}')"
            )

    def delete_checkpoint(self, filename: str) -> bool:
        """Xóa một checkpoint khỏi thư mục lưu trữ an toàn."""
        with self._lock:
            safe_filename = os.path.basename(filename)
            target_path = os.path.join(self.checkpoint_dir, safe_filename)
            if not os.path.exists(target_path):
                raise FileNotFoundError(f"Không tìm thấy file checkpoint: {safe_filename}")

            if self.current_checkpoint_path and os.path.abspath(target_path) == os.path.abspath(
                self.current_checkpoint_path
            ):
                raise ValueError("Không thể xóa checkpoint đang được nạp phục vụ suy luận!")

            os.remove(target_path)
            logger.info(f"🗑️ Đã xóa checkpoint: {safe_filename}")
            return True

    def stream_generate(
        self,
        prompt: str,
        config: GenerationConfig,
        backend: Optional[str] = None,
    ) -> Iterator[str]:
        """
        Thực hiện sinh văn bản trên worker thread và yield dữ liệu SSE format:
        event: token
        data: {"token": "..."}
        """
        if backend and backend.lower().strip() != self.current_backend:
            self.set_backend(backend)
        if not self.generator or not self.tokenizer:
            error_payload = json.dumps(
                {
                    "error": "Chưa có mô hình hoặc từ vựng nào được nạp. Hãy kiểm tra lại checkpoint.",
                }
            )
            yield f"data: {error_payload}\n\n"
            return

        streamer = TextIteratorStreamer(timeout=30.0)
        generation_error: List[Exception] = []
        tokens_emitted: List[str] = []
        t0 = time.time()

        def worker() -> None:
            try:
                assert self.generator is not None
                self.generator.generate(
                    prompt=prompt,
                    config=config,
                    streamer=streamer,
                    return_output=False,
                )
            except Exception as e:
                logger.exception(f"Lỗi worker suy luận: {e}")
                generation_error.append(e)
                # Đảm bảo streamer dừng để không treo hàng đợi
                streamer.on_finish()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        # Đẩy prompt ban đầu
        yield f"data: {json.dumps({'type': 'start', 'prompt': prompt})}\n\n"

        for token in streamer:
            tokens_emitted.append(token)
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

        thread.join(timeout=1.0)
        elapsed = time.time() - t0
        token_count = len(tokens_emitted)
        tps = round(token_count / elapsed, 2) if elapsed > 0 else 0.0

        if generation_error:
            yield f"data: {json.dumps({'type': 'error', 'message': str(generation_error[0])})}\n\n"
        else:
            full_text = prompt + "".join(tokens_emitted)
            yield f"data: {json.dumps({'type': 'done', 'full_text': full_text, 'token_count': token_count, 'elapsed_sec': round(elapsed, 3), 'tps': tps})}\n\n"
