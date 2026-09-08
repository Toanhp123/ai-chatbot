"""
CLI Điều Phối Hệ Thống AI Training Engine.
Composition Root: Khởi tạo toàn bộ linh kiện từ Cấu hình (Config-Driven) và tiêm phụ thuộc.
Hỗ trợ các lệnh:
  - check    : Chẩn đoán toàn diện phần cứng, GPU, VRAM, môi trường
  - estimate : Phân tích ngân sách VRAM theo các kịch bản
  - train    : Bắt đầu huấn luyện mô hình theo file cấu hình
  - generate : Sáng tác văn bản từ checkpoint đã huấn luyện
  - inspect  : Phân tích kiến trúc và cấu trúc tham số mô hình
  - gate     : Kiểm toán toàn diện chất lượng (Quality Gates)
"""

import argparse
import logging
import os
import sys

import torch

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

from src.core.config import EngineConfig, GenerationConfig, ModelConfig
from src.core.diagnostics import print_diagnostic_report
from src.core.exceptions import AIEngineError
from src.core.logging import configure_logging_from_system, setup_logger
from src.core.runtime import resolve_training_plan
from src.data.batch_provider import get_batch_provider
from src.data.cleaners import get_cleaner
from src.data.pipeline import DataPipeline
from src.data.tokenizers import load_tokenizer, load_tokenizer_state
from src.data.tokenizers.base import get_tokenizer_identity
from src.generation import BaseGenerator, ConsoleStreamer, get_generator
from src.models.registry import ModelRegistry
from src.training.callbacks import (
    ConsoleProgressCallback,
    EarlyStoppingCallback,
    ModelCheckpointCallback,
    SampleGenerationCallback,
)
from src.training.trainer import Trainer
from src.utils.device import resolve_device
from src.utils.seed import set_seed
from src.utils.tensor_inspector import print_model_summary

logger = logging.getLogger("ai-train")


def cmd_check(args: argparse.Namespace) -> None:
    setup_logger()
    print_diagnostic_report()


def cmd_estimate(args: argparse.Namespace) -> None:
    from src.core.diagnostics import analyze_vram_scenarios, print_vram_scenarios_table

    logger.info(f"Phân tích ngân sách VRAM cho cấu hình: {args.config}")
    overrides = getattr(args, "override", None)
    config = EngineConfig.from_yaml(args.config, overrides=overrides)
    configure_logging_from_system(config.system, name="ai-train")
    scenarios = analyze_vram_scenarios(
        model_config=config.model,
        training_config=config.training,
        system_config=config.system,
    )
    print_vram_scenarios_table(scenarios)


def cmd_inspect(args: argparse.Namespace) -> None:
    overrides = getattr(args, "override", None)
    config = EngineConfig.from_yaml(args.config, overrides=overrides)
    configure_logging_from_system(config.system, name="ai-train")
    model = ModelRegistry.create(config.model.name, config.model)
    print_model_summary(model)


def cmd_train(args: argparse.Namespace) -> None:
    logger.info(f"Nạp cấu hình từ: {args.config}")
    overrides = getattr(args, "override", None)
    config = EngineConfig.from_yaml(args.config, overrides=overrides)
    configure_logging_from_system(config.system, name="ai-train")

    # Pre-flight Memory Check
    from src.core.diagnostics import check_memory_feasibility

    runtime_plan = resolve_training_plan(config)

    feasible, mem_msg, _ = check_memory_feasibility(
        model_config=config.model,
        training_config=config.training,
        runtime_plan=runtime_plan,
    )
    if not feasible:
        logger.warning(f"⚠️ {mem_msg}")
    else:
        logger.info(f"✅ [Pre-flight Memory Check]: {mem_msg}")

    # Tùy chọn kiểm tra nhanh (quick check)
    if args.quick_check:
        config = config.copy(
            training=config.training.copy(
                max_iters=50,
                eval_interval=25,
                eval_iters=10,
            )
        )
        logger.info("⚡ Chế độ Quick Check: Huấn luyện nhanh 50 bước kiểm tra hệ thống.")

    set_seed(config.system.seed)

    # 1. Khởi tạo linh kiện Làm sạch (Cleaner) từ Config
    cleaner_kwargs = dict(config.data.cleaner_kwargs)
    cleaner_kwargs.setdefault("clean_line_numbers", config.data.clean_line_numbers)
    cleaner = get_cleaner(
        cleaner_type=config.data.cleaner_type,
        **cleaner_kwargs,
    )

    # 2. Chuẩn bị Dữ liệu qua DataPipeline (tiêm cleaner vào pipeline)
    train_data, val_data, tokenizer = DataPipeline.setup_data(
        config=config.data,
        cleaner=cleaner,
        block_size=config.model.block_size,
    )

    # 3. Khởi tạo Batch Provider từ Config (tensor hoặc dataloader)
    batch_provider = get_batch_provider(
        provider_type=config.data.batch_provider_type,
        train_data=train_data,
        val_data=val_data,
        block_size=config.model.block_size,
        num_workers=config.data.num_workers,
        pin_memory=config.data.pin_memory,
    )

    # Cập nhật kích thước từ vựng thực tế vào model config
    config = config.copy(model=config.model.copy(vocab_size=tokenizer.vocab_size))

    # 4. Khởi tạo mô hình qua ModelRegistry
    model = ModelRegistry.create(config.model.name, config.model)
    logger.info(f"Khởi tạo mô hình '{config.model.name}' với {model.get_num_params():,} tham số.")

    # 5. Thiết lập Callbacks (Dependency Injection: sample_fn được truyền vào từ Composition Root)
    sample_generator: BaseGenerator = get_generator(
        "local", model=model, tokenizer=tokenizer, device=runtime_plan.device
    )
    sample_gen_config = GenerationConfig(
        max_new_tokens=50 if args.quick_check else 100,
        temperature=0.8,
        top_k=40,
        use_cache=True,
    )

    def sample_fn(step: int) -> str:
        return sample_generator.generate("Trăm năm", config=sample_gen_config)

    callbacks = [
        ConsoleProgressCallback(log_interval=100 if not args.quick_check else 10),
        SampleGenerationCallback(sample_fn=sample_fn),
        EarlyStoppingCallback(
            monitor="val_loss",
            mode="min",
            patience=config.training.early_stopping_patience,
        ),
        # Checkpoint last: runtime snapshot sees the state changes of prior callbacks.
        ModelCheckpointCallback(
            save_dir=config.training.checkpoint_dir,
            filename=config.training.checkpoint_name,
            monitor="val_loss",
            mode="min",
            save_top_k=config.training.save_top_k,
            save_last=config.training.save_last,
            run_name=config.training.run_name,
        ),
    ]

    # 6. Khởi chạy Trainer
    trainer = Trainer(
        model=model,
        batch_provider=batch_provider,
        config=config,
        callbacks=callbacks,
        tokenizer=tokenizer,
        runtime_plan=runtime_plan,
    )
    trainer.train()


def load_generator_from_checkpoint(
    checkpoint_path: str,
    vocab_path: str,
    device: str = "auto",
    backend: str = "local",
) -> BaseGenerator:
    if not os.path.exists(checkpoint_path):
        raise AIEngineError(f"Không tìm thấy file checkpoint tại: {checkpoint_path}")
    target_device = resolve_device(device)
    checkpoint = torch.load(checkpoint_path, map_location=target_device, weights_only=True)
    checkpoint_identity = checkpoint.get("tokenizer_identity")
    if not isinstance(checkpoint_identity, dict):
        raise AIEngineError(
            "Checkpoint legacy không có tokenizer identity; từ chối nạp để tránh ánh xạ token sai."
        )
    checkpoint_version = int(checkpoint.get("checkpoint_version", 1))
    embedded_state = checkpoint.get("tokenizer_state")
    if checkpoint_version >= 3 and not isinstance(embedded_state, dict):
        raise AIEngineError("Checkpoint v3 thiếu tokenizer state bắt buộc.")
    if isinstance(embedded_state, dict):
        tokenizer = load_tokenizer_state(embedded_state)
    else:
        if not os.path.exists(vocab_path):
            raise AIEngineError(f"Không tìm thấy file từ vựng tại: {vocab_path}")
        tokenizer = load_tokenizer(vocab_path)

    if checkpoint_identity.get("fingerprint") != get_tokenizer_identity(tokenizer).get(
        "fingerprint"
    ):
        raise AIEngineError("Tokenizer/từ vựng không khớp checkpoint.")
    cfg_dict = checkpoint["config"]["model"]
    model_config = ModelConfig.from_kwargs_safe(cfg_dict, ignore_unknown=True)
    model = ModelRegistry.create(model_config.name, model_config)

    if isinstance(model, torch.nn.Module):
        model.load_state_dict(checkpoint["model_state_dict"])
    return get_generator(backend, model=model, tokenizer=tokenizer, device=target_device)


def cmd_generate(args: argparse.Namespace) -> None:
    setup_logger()
    checkpoint_path = args.checkpoint
    vocab_path = args.vocab
    backend = getattr(args, "backend", "local")

    logger.info(f"Tải Generator ({backend}) từ checkpoint: {checkpoint_path}")
    generator = load_generator_from_checkpoint(
        checkpoint_path, vocab_path, device="auto", backend=backend
    )

    is_greedy = getattr(args, "greedy", False)
    gen_config = GenerationConfig(
        max_new_tokens=args.tokens,
        temperature=0.0 if is_greedy else args.temp,
        top_k=args.top_k,
        top_p=args.top_p,
        min_p=getattr(args, "min_p", None),
        repetition_penalty=getattr(args, "repetition_penalty", 1.0),
        do_sample=not is_greedy,
        use_cache=not getattr(args, "no_cache", False),
    )

    streamer = ConsoleStreamer(delay=0.01)

    if args.prompt:
        print("\n📝 [KẾT QUẢ SINH]:")
        generator.generate(args.prompt, config=gen_config, streamer=streamer)
        return

    # Chế độ tương tác
    print("=" * 60)
    print("🤖 GIAO DIỆN SÁNG TÁC TƯƠNG TÁC MINI-GPT")
    print("Gõ câu mồi bất kỳ (hoặc 'q' để thoát):\n")
    while True:
        try:
            user_prompt = input("👉 Nhập câu mồi: ").strip()
            if user_prompt.lower() in ["q", "exit", "quit"]:
                break
            if not user_prompt:
                user_prompt = "Trăm năm trong cõi người ta,"
            print("\n📝 [AI đang sáng tác...]:")
            generator.generate(user_prompt, config=gen_config, streamer=streamer)
        except (KeyboardInterrupt, EOFError):
            print("\nĐã thoát.")
            break


def cmd_gate(args: argparse.Namespace) -> None:
    setup_logger()
    from scripts.check_all import main as run_quality_gates

    sys.exit(run_quality_gates())


def cmd_ui(args: argparse.Namespace) -> None:
    setup_logger()
    try:
        import uvicorn
    except ImportError:
        logger.error("Chưa cài đặt uvicorn. Chạy: pip install uvicorn fastapi")
        sys.exit(1)

    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", 8000)
    reload = getattr(args, "reload", False)

    logger.info(f"🚀 Khởi chạy AI Studio Web Dashboard tại: http://{host}:{port}")
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Training Engine - Modular AI Pipeline Architecture"
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    # check
    p_check = subparsers.add_parser("check", help="Kiểm tra chẩn đoán hệ thống và phần cứng")
    p_check.set_defaults(func=cmd_check)

    # estimate
    p_est = subparsers.add_parser(
        "estimate", help="Dự toán ngân sách VRAM và phân tích các kịch bản huấn luyện"
    )
    p_est.add_argument(
        "--config", default="configs/truyen_kieu.yaml", help="Đường dẫn file cấu hình"
    )
    p_est.add_argument(
        "--override",
        nargs="*",
        default=[],
        help="Ghi đè tham số cấu hình động (vd: training.batch_size=32 model.dropout=0.2)",
    )
    p_est.set_defaults(func=cmd_estimate)

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Phân tích kiến trúc mô hình")
    p_inspect.add_argument(
        "--config", default="configs/truyen_kieu.yaml", help="Đường dẫn file cấu hình"
    )
    p_inspect.add_argument(
        "--override",
        nargs="*",
        default=[],
        help="Ghi đè tham số cấu hình động (vd: training.batch_size=32 model.dropout=0.2)",
    )
    p_inspect.set_defaults(func=cmd_inspect)

    # train
    p_train = subparsers.add_parser("train", help="Huấn luyện mô hình")
    p_train.add_argument(
        "--config", default="configs/truyen_kieu.yaml", help="Đường dẫn file cấu hình"
    )
    p_train.add_argument(
        "--override",
        nargs="*",
        default=[],
        help="Ghi đè tham số cấu hình động (vd: training.batch_size=32 model.dropout=0.2)",
    )
    p_train.add_argument(
        "--quick-check", action="store_true", help="Chạy thử 50 bước kiểm tra pipeline"
    )
    p_train.set_defaults(func=cmd_train)

    # generate
    p_gen = subparsers.add_parser("generate", help="Sinh văn bản từ checkpoint đã huấn luyện")
    p_gen.add_argument(
        "--checkpoint", default="checkpoints/best_model.pt", help="File checkpoint mô hình"
    )
    p_gen.add_argument("--vocab", default="data/vocab.json", help="File từ điển vocab.json")
    p_gen.add_argument("--prompt", default=None, help="Câu mồi bắt đầu")
    p_gen.add_argument("--tokens", type=int, default=200, help="Số ký tự sinh")
    p_gen.add_argument("--temp", type=float, default=0.75, help="Nhiệt độ sáng tạo (0.5 - 1.0)")
    p_gen.add_argument("--top_k", type=int, default=40, help="Top-K sampling")
    p_gen.add_argument("--top_p", type=float, default=0.9, help="Top-P nucleus sampling")
    p_gen.add_argument(
        "--min_p",
        type=float,
        default=None,
        help="Min-P truncation sampling (0.0 - 1.0, vd: 0.05)",
    )
    p_gen.add_argument(
        "--repetition_penalty",
        type=float,
        default=1.0,
        help="Hệ số phạt lặp từ (>= 1.0, vd: 1.15)",
    )
    p_gen.add_argument(
        "--greedy",
        action="store_true",
        help="Chế độ Greedy Search xác định (tương đương temperature=0, do_sample=False)",
    )
    p_gen.add_argument(
        "--no_cache",
        action="store_true",
        help="Vô hiệu hóa KV-Cache (chạy chế độ không cache O(T^2))",
    )
    p_gen.add_argument(
        "--backend",
        default="local",
        help="Backend suy luận trong GeneratorRegistry (mặc định: 'local')",
    )
    p_gen.set_defaults(func=cmd_generate)

    # gate (Quality Gates & Architecture check)
    p_gate = subparsers.add_parser(
        "gate", help="Kiểm toán toàn diện chất lượng (Format, Lint, Architecture, Tests)"
    )
    p_gate.set_defaults(func=cmd_gate)

    # ui (Web Dashboard)
    p_ui = subparsers.add_parser("ui", help="Khởi chạy giao diện Web AI Studio Dashboard hiện đại")
    p_ui.add_argument(
        "--host", default="127.0.0.1", help="Địa chỉ host máy chủ (mặc định: 127.0.0.1)"
    )
    p_ui.add_argument("--port", type=int, default=8000, help="Cổng dịch vụ (mặc định: 8000)")
    p_ui.add_argument("--reload", action="store_true", help="Tự động nạp lại mã nguồn khi sửa đổi")
    p_ui.set_defaults(func=cmd_ui)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        args.func(args)
    except KeyboardInterrupt:
        logger.info("\n🛑 Đã nhận tín hiệu ngắt (Ctrl+C). Đang thoát chương trình an toàn...")
        sys.exit(0)
    except AIEngineError as e:
        logger.error(f"❌ [Lỗi Hệ Thống]: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ [Lỗi Không Mong Muốn]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
