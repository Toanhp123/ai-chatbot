"""
API Routes package for AI Studio Web Dashboard.
"""

from src.ui.routes.diagnostics import router as diagnostics_router
from src.ui.routes.explorer import router as explorer_router
from src.ui.routes.inference import router as inference_router
from src.ui.routes.training import router as training_router

__all__ = [
    "inference_router",
    "training_router",
    "diagnostics_router",
    "explorer_router",
]
