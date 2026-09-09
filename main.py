"""CLI adapter for the AI Training Engine application layer.

The CLI owns argument parsing, terminal input/output and process exit codes only.
Use-case orchestration lives under ``src.application``; domain/module construction
must not be recreated here.
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.adapters.cli import ConsoleTrainingObserver
from src.adapters.config import YamlConfigProvider
from src.application.config import ConfigRequest, ConfigurationService
from src.application.diagnostics import DiagnosticsApplicationService
from src.application.errors import AIEngineError
from src.application.inference import (
    GenerationCommand,
    GenerationOverrides,
    InferenceService,
)
from src.application.inference import (
    load_generator_from_checkpoint as _load_generator_from_checkpoint,
)
from src.application.runtime import ApplicationRuntimeService
from src.application.training import TrainingApplicationService, TrainingCommand

logger = logging.getLogger("ai-train")


if sys.platform == "win32":
    try:
        reconfigure_out = getattr(sys.stdout, "reconfigure", None)
        if callable(reconfigure_out):
            reconfigure_out(encoding="utf-8", errors="replace")
        reconfigure_err = getattr(sys.stderr, "reconfigure", None)
        if callable(reconfigure_err):
            reconfigure_err(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _config_service() -> ConfigurationService:
    return ConfigurationService(YamlConfigProvider())


def _config_request(args: argparse.Namespace) -> ConfigRequest:
    return ConfigRequest.from_values(
        getattr(args, "config", None),
        getattr(args, "override", None),
    )


def _configure_from_request(
    config_service: ConfigurationService,
    args: argparse.Namespace,
):
    config = config_service.resolve(_config_request(args))
    ApplicationRuntimeService.configure_logging(config, name="ai-train")
    return config


def cmd_check(args: argparse.Namespace) -> None:
    config_service = _config_service()
    _configure_from_request(config_service, args)
    DiagnosticsApplicationService(config_service).print_system_report()


def cmd_estimate(args: argparse.Namespace) -> None:
    config_service = _config_service()
    config = _configure_from_request(config_service, args)
    config_service.activate(config)
    logger.info(
        "Phân tích ngân sách VRAM cho cấu hình: %s", args.config or config_service.default_path
    )
    DiagnosticsApplicationService(config_service).print_scenarios_from_config(
        None,
        (),
    )


def cmd_inspect(args: argparse.Namespace) -> None:
    config_service = _config_service()
    config = _configure_from_request(config_service, args)
    config_service.activate(config)
    DiagnosticsApplicationService(config_service).print_inspect(None, ())


def cmd_train(args: argparse.Namespace) -> None:
    config_service = _config_service()
    application = TrainingApplicationService(config_service)
    plan = application.plan(
        TrainingCommand(
            config_path=getattr(args, "config", None),
            overrides=tuple(getattr(args, "override", None) or ()),
            quick_check=bool(getattr(args, "quick_check", False)),
        )
    )
    ApplicationRuntimeService.configure_logging(plan.requested_config, name="ai-train")
    logger.info("Nạp cấu hình từ: %s", args.config or config_service.default_path)
    if plan.feasibility.feasible:
        logger.info("✅ [Pre-flight Memory Check]: %s", plan.feasibility.message)
    else:
        logger.warning("⚠️ %s", plan.feasibility.message)
    if getattr(args, "quick_check", False):
        logger.info("⚡ Chế độ Quick Check: Huấn luyện nhanh 50 bước kiểm tra hệ thống.")

    prepared = application.prepare(
        plan,
        observer=ConsoleTrainingObserver(),
        log_interval=10 if getattr(args, "quick_check", False) else 100,
    )
    application.execute(prepared, plan)


def load_generator_from_checkpoint(
    checkpoint_path: str,
    vocab_path: str,
    device: str = "auto",
    backend: str = "local",
):
    """Compatibility facade over the canonical application checkpoint loader."""
    return _load_generator_from_checkpoint(
        checkpoint_path,
        vocab_path,
        device=device,
        backend=backend,
    )


def _generation_overrides(args: argparse.Namespace) -> GenerationOverrides:
    no_cache = getattr(args, "no_cache", None)
    return GenerationOverrides(
        max_new_tokens=getattr(args, "tokens", None),
        temperature=getattr(args, "temp", None),
        top_k=getattr(args, "top_k", None),
        top_p=getattr(args, "top_p", None),
        min_p=getattr(args, "min_p", None),
        repetition_penalty=getattr(args, "repetition_penalty", None),
        greedy=getattr(args, "greedy", None),
        use_cache=None if no_cache is None else not no_cache,
    )


def _render_generation(
    inference: InferenceService,
    *,
    prompt: str,
    overrides: GenerationOverrides,
    backend: str,
) -> None:
    session = inference.begin_generation_command(
        GenerationCommand.create(prompt=prompt, overrides=overrides, backend=backend)
    )
    for event in session.iter_events():
        event_type = event.get("type")
        if event_type == "token":
            print(str(event.get("token", "")), end="", flush=True)
        elif event_type == "error":
            message = event.get("message") or event.get("detail") or "Lỗi sinh văn bản."
            raise AIEngineError(str(message))
    print()


def cmd_generate(args: argparse.Namespace) -> None:
    config_service = _config_service()
    config = _configure_from_request(config_service, args)
    config_service.activate(config)
    inference = InferenceService.from_engine_config(config, config_service=config_service)
    backend = getattr(args, "backend", None) or inference.current_backend
    if getattr(args, "vocab", None):
        inference.set_vocab_path(args.vocab)
    checkpoint = getattr(args, "checkpoint", None) or inference.configured_checkpoint_path
    logger.info("Tải Generator (%s) từ checkpoint: %s", backend, checkpoint)
    inference.load_checkpoint(checkpoint, backend=backend)
    overrides = _generation_overrides(args)

    if args.prompt:
        print("\n📝 [KẾT QUẢ SINH]:")
        _render_generation(inference, prompt=args.prompt, overrides=overrides, backend=backend)
        return

    print("=" * 60)
    print("🤖 GIAO DIỆN SÁNG TÁC TƯƠNG TÁC MINI-GPT")
    print("Gõ câu mồi bất kỳ (hoặc 'q' để thoát):\n")
    while True:
        try:
            user_prompt = input("👉 Nhập câu mồi: ").strip()
            if user_prompt.lower() in {"q", "exit", "quit"}:
                break
            if not user_prompt:
                user_prompt = "Trăm năm trong cõi người ta,"
            print("\n📝 [AI đang sáng tác...]:")
            _render_generation(
                inference,
                prompt=user_prompt,
                overrides=overrides,
                backend=backend,
            )
        except (KeyboardInterrupt, EOFError):
            print("\nĐã thoát.")
            break


def cmd_gate(args: argparse.Namespace) -> None:
    del args
    raise SystemExit(DiagnosticsApplicationService.run_quality_gates_cli())


def cmd_ui(args: argparse.Namespace) -> None:
    config_service = _config_service()
    config = config_service.resolve()
    ApplicationRuntimeService.configure_logging(config, name="ai-train")
    try:
        import uvicorn
    except ImportError:
        logger.error("Chưa cài đặt uvicorn. Chạy: pip install uvicorn fastapi")
        raise SystemExit(1)

    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8000)
    reload = getattr(args, "reload", False)
    logger.info("🚀 Khởi chạy AI Studio Web Dashboard tại: http://%s:%s", host, port)
    uvicorn_kwargs = {
        "factory": True,
        "host": host,
        "port": port,
        "reload": reload,
    }
    if reload:
        uvicorn_kwargs["reload_dirs"] = ["src"]
        uvicorn_kwargs["reload_excludes"] = [
            "checkpoints/*",
            "runs/*",
            "logs/*",
            "*.pt",
            "*.log",
            "*.jsonl",
            "data/processed/*",
        ]
    uvicorn.run("src.ui.app:create_app", **uvicorn_kwargs)


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        default=None,
        help="Đường dẫn file cấu hình; bỏ trống để dùng ConfigProvider mặc định",
    )
    parser.add_argument(
        "--override",
        nargs="*",
        default=[],
        help="Ghi đè cấu hình động (vd: training.batch_size=32 model.dropout=0.2)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Training Engine - Modular AI Pipeline Architecture"
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    p_check = subparsers.add_parser("check", help="Kiểm tra chẩn đoán hệ thống và phần cứng")
    p_check.set_defaults(func=cmd_check)

    p_est = subparsers.add_parser(
        "estimate", help="Dự toán ngân sách VRAM và phân tích các kịch bản huấn luyện"
    )
    _add_config_arguments(p_est)
    p_est.set_defaults(func=cmd_estimate)

    p_inspect = subparsers.add_parser("inspect", help="Phân tích kiến trúc mô hình")
    _add_config_arguments(p_inspect)
    p_inspect.set_defaults(func=cmd_inspect)

    p_train = subparsers.add_parser("train", help="Huấn luyện mô hình")
    _add_config_arguments(p_train)
    p_train.add_argument(
        "--quick-check", action="store_true", help="Chạy thử 50 bước kiểm tra pipeline"
    )
    p_train.set_defaults(func=cmd_train)

    p_gen = subparsers.add_parser("generate", help="Sinh văn bản từ checkpoint đã huấn luyện")
    _add_config_arguments(p_gen)
    p_gen.add_argument(
        "--checkpoint", default=None, help="File checkpoint; bỏ trống để dùng cấu hình canonical"
    )
    p_gen.add_argument(
        "--vocab", default=None, help="File vocab; bỏ trống để dùng cấu hình canonical"
    )
    p_gen.add_argument("--prompt", default=None, help="Câu mồi bắt đầu")
    p_gen.add_argument("--tokens", type=int, default=None, help="Ghi đè max_new_tokens")
    p_gen.add_argument("--temp", type=float, default=None, help="Ghi đè temperature")
    p_gen.add_argument("--top_k", type=int, default=None, help="Ghi đè Top-K sampling")
    p_gen.add_argument("--top_p", type=float, default=None, help="Ghi đè Top-P sampling")
    p_gen.add_argument("--min_p", type=float, default=None, help="Ghi đè Min-P sampling")
    p_gen.add_argument(
        "--repetition_penalty", type=float, default=None, help="Ghi đè hệ số phạt lặp"
    )
    p_gen.add_argument(
        "--greedy", action="store_true", default=None, help="Bật Greedy Search xác định"
    )
    p_gen.add_argument("--no_cache", action="store_true", default=None, help="Vô hiệu hóa KV-Cache")
    p_gen.add_argument(
        "--backend", default=None, help="Backend suy luận; bỏ trống để dùng application default"
    )
    p_gen.set_defaults(func=cmd_generate)

    p_gate = subparsers.add_parser(
        "gate", help="Kiểm toán toàn diện chất lượng (Format, Lint, Architecture, Tests)"
    )
    p_gate.set_defaults(func=cmd_gate)

    p_ui = subparsers.add_parser("ui", help="Khởi chạy giao diện Web AI Studio Dashboard")
    p_ui.add_argument("--host", default="127.0.0.1", help="Địa chỉ host máy chủ")
    p_ui.add_argument("--port", type=int, default=8000, help="Cổng dịch vụ")
    p_ui.add_argument("--reload", action="store_true", help="Tự động nạp lại mã nguồn")
    p_ui.set_defaults(func=cmd_ui)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    try:
        args.func(args)
    except KeyboardInterrupt:
        logger.info("\n🛑 Đã nhận tín hiệu ngắt (Ctrl+C). Đang thoát chương trình an toàn...")
        raise SystemExit(0)
    except AIEngineError as exc:
        logger.error("❌ [Lỗi Hệ Thống]: %s", exc)
        raise SystemExit(1)
    except Exception as exc:
        logger.exception("❌ [Lỗi Không Mong Muốn]: %s", exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
