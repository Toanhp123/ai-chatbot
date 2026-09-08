"""
Các chiến lược lấy mẫu xác suất (Sampling Strategies):
- TopKTopPSampler: Lấy mẫu kết hợp Temperature + Top-K + Top-P (Nucleus) + Min-P.
- sample_next_token: Hàm tiện ích lấy mẫu trực tiếp từ logits với hỗ trợ Greedy Search.
- apply_repetition_penalty: Thuật toán phạt lặp từ theo chuẩn Keskar et al. (CTRL / Hugging Face).
"""

from typing import Collection, Optional

import torch
import torch.nn.functional as F

from src.core.exceptions import SamplingError


def apply_repetition_penalty(
    logits: torch.Tensor,
    generated_tokens: Collection[int],
    penalty: float = 1.0,
) -> torch.Tensor:
    """
    Áp dụng hệ số phạt lặp từ (Repetition Penalty) theo chuẩn Keskar et al.:
    - Nếu logit > 0: logit = logit / penalty
    - Nếu logit <= 0: logit = logit * penalty
    Giúp triệt tiêu hiện tượng mô hình bị rơi vào vòng lặp vô tận (Repetition Loop).
    """
    if penalty == 1.0 or not generated_tokens:
        return logits

    unique_tokens = sorted(
        token_id
        for token_id in set(generated_tokens)
        if isinstance(token_id, int) and 0 <= token_id < logits.size(-1)
    )
    if not unique_tokens:
        return logits

    token_index = torch.tensor(unique_tokens, dtype=torch.long, device=logits.device)
    scores = logits.index_select(-1, token_index)
    penalized = torch.where(scores > 0, scores / penalty, scores * penalty)
    logits.index_copy_(-1, token_index, penalized)

    return logits


class TopKTopPSampler:
    """Bộ lấy mẫu theo chiến lược Temperature + Top-K + Top-P Nucleus + Min-P + Greedy Search."""

    def __init__(
        self,
        temperature: float = 0.8,
        top_k: Optional[int] = 40,
        top_p: Optional[float] = 0.9,
        min_p: Optional[float] = None,
        do_sample: bool = True,
    ) -> None:
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.min_p = min_p
        self.do_sample = do_sample

    def sample(self, logits: torch.Tensor) -> torch.Tensor:
        return sample_next_token(
            logits,
            temperature=self.temperature,
            top_k=self.top_k,
            top_p=self.top_p,
            min_p=self.min_p,
            do_sample=self.do_sample,
        )


def sample_next_token(
    logits: torch.Tensor,
    temperature: float = 0.8,
    top_k: Optional[int] = 40,
    top_p: Optional[float] = 0.9,
    min_p: Optional[float] = None,
    do_sample: bool = True,
) -> torch.Tensor:
    """
    Nhận logits 1D hoặc (1, vocab_size) của token cuối cùng và trả về token ID được lấy mẫu:
    1. Nếu do_sample=False hoặc temperature <= 0.0: Greedy Search (Argmax) thuần túy.
    2. Áp dụng Temperature Scaling.
    3. Lọc Top-K (cố định số lượng ứng viên có xác suất cao nhất).
    4. Lọc Min-P (loại bỏ token có xác suất < min_p * p_max).
    5. Lọc Top-P Nucleus (cắt đuôi xác suất tích lũy).
    6. Lấy mẫu ngẫu nhiên từ phân phối xác suất đã chuẩn hóa.
    """
    if logits.dim() == 1:
        logits = logits.unsqueeze(0)

    # 1. Greedy Search (Xác định 100%, nhanh nhất)
    if not do_sample or temperature <= 0.0:
        return torch.argmax(logits, dim=-1)

    # 2. Áp dụng nhiệt độ (Temperature Scaling)
    logits = logits / max(temperature, 1e-5)

    # 3. Lọc Top-K
    if top_k is not None and top_k > 0:
        v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
        logits[logits < v[:, [-1]]] = -float("Inf")

    # 4. Lọc Min-P (Cắt đuôi động theo tỷ lệ với token dẫn đầu)
    if min_p is not None and 0.0 < min_p < 1.0:
        p = F.softmax(logits, dim=-1)
        p_max = p.max(dim=-1, keepdim=True).values
        threshold = min_p * p_max
        logits[p < threshold] = -float("Inf")

    # 5. Lọc Top-P (Nucleus Sampling)
    if top_p is not None and 0.0 < top_p < 1.0:
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

        # Loại bỏ các token có xác suất tích lũy vượt quá top_p
        sorted_indices_to_remove = cumulative_probs > top_p
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0

        indices_to_remove = sorted_indices_to_remove.scatter(
            1, sorted_indices, sorted_indices_to_remove
        )
        logits[indices_to_remove] = -float("Inf")

    # 6. Lấy mẫu ngẫu nhiên theo phân phối xác suất
    probs = F.softmax(logits, dim=-1)
    try:
        next_token = torch.multinomial(probs, num_samples=1)
    except RuntimeError as exc:
        raise SamplingError(cause=exc) from exc
    return next_token.squeeze(-1)


__all__ = [
    "TopKTopPSampler",
    "sample_next_token",
    "apply_repetition_penalty",
]
