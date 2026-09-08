"""
Tiện ích thiết lập seed ngẫu nhiên đảm bảo tính tái lập (Reproducibility).
"""

import random

import numpy as np
import torch


def set_seed(seed: int = 1337, deterministic: bool = True):
    """Cài đặt seed cho tất cả các thư viện ngẫu nhiên."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        if deterministic:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
