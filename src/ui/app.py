"""
FastAPI Application Factory cho AI Studio Web Dashboard.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.adapters.config import YamlConfigProvider
from src.application.config import ConfigurationService
from src.application.diagnostics import DiagnosticsApplicationService
from src.application.explorer import ExplorerApplicationService
from src.application.inference import InferenceService
from src.application.runtime import AcceleratorCoordinator
from src.application.training import (
    TrainingApplicationService,
    TrainingLaunchApplicationService,
    TrainingService,
)
from src.ui.errors import register_ai_engine_error_handlers
from src.ui.routes.diagnostics import router as diagnostics_router
from src.ui.routes.explorer import router as explorer_router
from src.ui.routes.inference import router as inference_router
from src.ui.routes.training import router as training_router


def create_app() -> FastAPI:
    """Tạo và cấu hình ứng dụng FastAPI AI Studio Dashboard."""
    app = FastAPI(
        title="AI Training & Inference Studio",
        description="Bảng điều khiển Sáng tác, Huấn luyện và Chẩn đoán AI Modular Monolith",
        version="1.0.0",
    )
    register_ai_engine_error_handlers(app)

    # Cấu hình CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # One composition root: adapters provide config I/O, application services own use cases.
    config_provider = YamlConfigProvider()
    config_service = ConfigurationService(config_provider)
    boot_config = config_service.activate(config_service.resolve())
    app.state.configuration_service = config_service
    app.state.config_path = os.path.realpath(os.path.abspath(config_service.default_path))
    app.state.accelerator_coordinator = AcceleratorCoordinator()
    app.state.inference_service = InferenceService.from_engine_config(
        boot_config,
        accelerator_coordinator=app.state.accelerator_coordinator,
        config_service=config_service,
    )
    app.state.training_application = TrainingApplicationService(config_service)
    app.state.training_service = TrainingService(
        accelerator_coordinator=app.state.accelerator_coordinator,
        training_application=app.state.training_application,
    )
    app.state.training_launch_service = TrainingLaunchApplicationService(
        training_service=app.state.training_service,
        inference_service=app.state.inference_service,
        config_service=config_service,
    )
    app.state.diagnostics_service = DiagnosticsApplicationService(config_service)
    app.state.explorer_service = ExplorerApplicationService(config_service)

    # Đăng ký các Route API
    app.include_router(inference_router)
    app.include_router(training_router)
    app.include_router(diagnostics_router)
    app.include_router(explorer_router)

    # Cấu hình Modern SPA Dist (React 19 + TypeScript + Vite)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    dist_assets = os.path.join(dist_dir, "assets")
    dist_index = os.path.join(dist_dir, "index.html")

    if os.path.exists(dist_assets):
        app.mount("/assets", StaticFiles(directory=dist_assets), name="spa_assets")

    @app.get("/favicon.svg")
    async def favicon_svg():
        fav_path = os.path.join(dist_dir, "favicon.svg")
        if os.path.exists(fav_path):
            return FileResponse(fav_path)
        return HTMLResponse(status_code=404)

    @app.get("/healthz")
    async def health_check():
        return {"status": "ok", "service": "ai-studio"}

    def _serve_spa_index():
        if os.path.exists(dist_index):
            return FileResponse(dist_index)
        return HTMLResponse(
            content="""<!doctype html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>AI Studio • Aura AI (Sáng Tác & Làm Việc)</title>
    <style>
        body { font-family: system-ui, sans-serif; background: #faf8f5; color: #292524; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .box { background: white; border: 1px solid #e7e5e4; border-radius: 16px; padding: 32px; max-width: 500px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        h1 { font-size: 20px; color: #1c1917; margin-bottom: 8px; }
        p { font-size: 13px; color: #78716c; line-height: 1.6; }
        code { background: #f5f5f4; padding: 3px 8px; border-radius: 6px; font-family: monospace; font-size: 12px; }
    </style>
</head>
<body>
    <div class="box">
        <h1>AI Studio • Trợ Lý Aura AI (Sáng Tác & Làm Việc)</h1>
        <p>Giao diện người dùng hiện đại (SPA) chưa được biên dịch vào <code>src/ui/dist</code>.</p>
        <p>Để build giao diện sản xuất, hãy chạy lệnh:<br><code>cd frontend &amp;&amp; npm run build</code></p>
        <p>Hoặc chạy máy chủ phát triển React tại:<br><code>cd frontend &amp;&amp; npm run dev</code></p>
    </div>
</body>
</html>""",
            status_code=200,
        )

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return _serve_spa_index()

    # SPA Client Routing Fallback: Cho phép F5 / truy cập trực tiếp các route như /training, /diagnostics,...
    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("assets/"):
            return HTMLResponse(status_code=404, content="Not Found")
        return _serve_spa_index()

    return app
