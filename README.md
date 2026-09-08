# 🏛️ AI Engine: Kiến Trúc Modular Monolith & Clean Architecture

Hệ thống huấn luyện và suy luận mô hình ngôn ngữ tự hồi quy (**Autoregressive Language Model - Transformer Decoder**) được xây dựng theo triết lý **Modular Monolith** kết hợp **Clean Architecture**.

Hệ thống phân tách ranh giới rõ ràng giữa các tầng nghiệp vụ, áp dụng nguyên lý **Dependency Inversion**, tự chủ lớp cơ sở trừu tượng (`Base*`) trong từng domain, và được bảo vệ nghiêm ngặt bởi **6 Quality Gates** (AST Architecture Guardian, Pyright Strict Type Checking, Ruff Linter/Formatter, Diagnostics, và PyTest).

---

## 🏗️ Cấu Trúc Dự Án Thực Tế (Modular Monolith)

```text
ai-train/
│
├── configs/                            # Cấu hình tập trung (YAML)
│   └── truyen_kieu.yaml                # Cấu hình chuẩn hóa cho tác phẩm Truyện Kiều
│
├── checkpoints/                        # Thư mục lưu trữ model checkpoints & metadata
│   └── best_model.pt                   # Checkpoint mô hình tối ưu đã huấn luyện
│
├── data/                               # Dữ liệu phục vụ huấn luyện
│   ├── input.txt                       # Dữ liệu văn bản Truyện Kiều đã làm sạch
│   └── vocab.json                      # Bảng từ vựng ký tự (129 ký tự)
│
├── logs/                               # Thư mục lưu log xoay vòng (Rotating File Logs)
│   └── engine.log                      # Log chi tiết có timestamp, log level, module, dòng code
│
├── src/                                # Gói mã nguồn chính (Modular Monolith)
│   ├── core/                           # [TẦNG CORE & HỆ THỐNG NỀN TẢNG]
│   │   ├── config/                     # Hệ thống Config 2.0 (Dataclass, YAML parsing, validation, override)
│   │   │   ├── base.py                 # BaseConfig, cơ chế from_kwargs_safe & chống typo
│   │   │   ├── system.py               # SystemConfig (seed, device, precision, logging)
│   │   │   ├── data.py                 # DataConfig (đường dẫn, split ratio, cleaner/tokenizer type)
│   │   │   ├── model.py                # ModelConfig (block_size, n_embd, n_head, n_layer, dropout)
│   │   │   ├── training.py             # TrainingConfig (batch_size, lr, warmup, optimizers, accum)
│   │   │   ├── generation.py           # GenerationConfig (temperature, top_k, top_p, min_p, repetition)
│   │   │   └── engine.py               # EngineConfig (Aggregator hợp nhất các config con)
│   │   ├── diagnostics/                # Health check & phân tích phần cứng đa chiều
│   │   │   ├── hardware.py             # Giám sát CPU, RAM hệ thống, GPU & VRAM
│   │   │   ├── storage.py              # Kiểm tra dung lượng đĩa trống & quyền I/O đọc/ghi
│   │   │   ├── system.py               # Thu thập phiên bản OS, Python, PyTorch, CUDA, cuDNN
│   │   │   ├── estimator.py            # Dự toán ngân sách VRAM theo nhiều kịch bản huấn luyện
│   │   │   ├── reporter.py             # Kết xuất báo cáo chẩn đoán bằng Rich Terminal Table
│   │   │   └── runner.py               # Bộ điều phối chạy chẩn đoán toàn diện
│   │   ├── exceptions.py               # Họ ngoại lệ chuẩn hóa kế thừa AIEngineError có ErrorCode
│   │   └── logging.py                  # Structured Logger đa kênh (Rich Console + Rotating File)
│   │
│   ├── data/                           # [DOMAIN DỮ LIỆU]
│   │   ├── cleaners/                   # Hệ thống làm sạch văn bản (BaseCleaner & CleanerRegistry)
│   │   │   ├── base.py                 # Lớp cơ sở trừu tượng BaseCleaner
│   │   │   ├── standard.py             # DefaultTextCleaner (Unicode NFC, chuẩn hóa dòng)
│   │   │   ├── gemini.py               # Gemini-compatible TextCleaner
│   │   │   └── registry.py             # CleanerRegistry cắm rút linh hoạt
│   │   ├── tokenizers/                 # Hệ thống mã hóa từ vựng (BaseTokenizer & TokenizerRegistry)
│   │   │   ├── base.py                 # Lớp cơ sở trừu tượng BaseTokenizer
│   │   │   ├── char.py                 # CharTokenizer (mã hóa cấp ký tự tiếng Việt)
│   │   │   ├── byte.py                 # ByteTokenizer (mã hóa cấp byte UTF-8, zero OOV)
│   │   │   ├── gemini.py               # Alias legacy tương thích, dùng semantics ByteTokenizer
│   │   │   └── registry.py             # TokenizerRegistry & hàm tự nạp load_tokenizer
│   │   ├── batch_provider.py           # BaseBatchProvider, TensorBatchProvider (GPU in-memory), DataLoaderBatchProvider
│   │   ├── dataset.py                  # PyTorch TextDataset phục vụ batching
│   │   ├── pipeline.py                 # DataPipeline điều phối nạp dữ liệu, làm sạch và token hóa
│   │   └── constants.py                # Hằng số đặc tả dữ liệu
│   │
│   ├── models/                         # [DOMAIN MÔ HÌNH NƠ-RON]
│   │   ├── base.py                     # Lớp cơ sở trừu tượng BaseModel
│   │   ├── registry.py                 # ModelRegistry (Factory Pattern qua @ModelRegistry.register)
│   │   ├── layers/                     # Các khối nơ-ron nền tảng
│   │   │   ├── attention.py            # Multi-Head Causal Self-Attention (FlashAttention / Cutlass / Math)
│   │   │   ├── block.py                # Transformer Block chuẩn Pre-LN
│   │   │   ├── mlp.py                  # Feed-Forward Network (GELU)
│   │   │   ├── norm.py                 # LayerNorm & RMSNorm
│   │   │   └── rotary.py               # Rotary Positional Embedding (RoPE)
│   │   └── architectures/              # Kiến trúc mô hình hoàn chỉnh
│   │       ├── minigpt.py              # MiniGPT (Decoder-only Transformer có Weight Tying)
│   │       └── llama.py                # Biến thể LLaMA (RMSNorm + RoPE + SwiGLU)
│   │
│   ├── training/                       # [DOMAIN HUẤN LUYỆN]
│   │   ├── trainer.py                  # Trainer Engine độc lập (Gradient Accumulation, AMP FP16, Graceful Stop)
│   │   ├── optimizers.py               # Tách biệt Weight Decay + Cosine Annealing with Warmup
│   │   └── callbacks/                  # Hệ thống Hook Callbacks độc lập qua TrainerProtocol
│   │       ├── base.py                 # BaseCallback & TrainerProtocol (PEP 544 loose coupling)
│   │       ├── progress.py             # ConsoleProgressCallback (theo dõi tiến độ theo step)
│   │       ├── checkpoint.py           # ModelCheckpointCallback (lưu checkpoint tối ưu theo monitor metric)
│   │       ├── sample.py               # SampleGenerationCallback (sinh văn bản kiểm tra chất lượng định kỳ)
│   │       └── early_stopping.py       # EarlyStoppingCallback (dừng sớm khi val_loss không cải thiện)
│   │
│   ├── generation/                     # [DOMAIN SUY LUẬN & SINH VĂN BẢN]
│   │   ├── base.py                     # BaseGenerator & GenerationOutput (metadata TPS, elapsed_time)
│   │   ├── registry.py                 # GeneratorRegistry (cắm rút Local PyTorch, Cloud APIs...)
│   │   ├── generator.py                # TextGenerator (Tối ưu KV-Cache O(1), Repetition Penalty, Stop Tokens)
│   │   ├── samplers.py                 # Thuật toán lấy mẫu: Greedy, Temperature, Top-K, Top-P, Min-P
│   │   └── streamers.py                # Streamers: ConsoleStreamer (CLI) & TextIteratorStreamer (Web API/SSE)
│   │
│   ├── ui/                             # [TẦNG TRÌNH DIỄN & GIAO DIỆN WEB (AI STUDIO)]
│   │   ├── app.py                      # FastAPI Application Factory, CORS & SPA Server
│   │   ├── routes/                     # API Routers: inference, training, diagnostics, explorer
│   │   ├── services/                   # Background Services: inference streaming & training thread
│   │   └── dist/                       # SPA Production Bundle (React 19 + TypeScript + Vite)
│   │
│   └── utils/                          # [TIỆN ÍCH HỆ THỐNG]
│       ├── seed.py                     # Cài đặt seed ngẫu nhiên xác định (Deterministic Seeding)
│       └── tensor_inspector.py         # Kiểm tra tính hợp lệ của Tensor, tránh NaN/Inf, đo Peak VRAM
│
├── scripts/                            # Kịch bản kiểm toán & công cụ tự động
│   ├── check_all.py                    # Unified Quality Gates Runner (Chạy đồng thời 6 chốt chặn chất lượng)
│   ├── check_architecture.py           # AST Architecture Boundary Linter (Khóa chặt ranh giới phụ thuộc)
│   ├── pre-commit.bat                  # Hook tự động chạy quality gates trên Windows
│   └── pre-commit.sh                   # Hook tự động chạy quality gates trên Linux/macOS
│
├── tests/                              # Bộ kiểm thử tự động toàn diện (15 Test Suites, 136 Tests)
│   ├── test_architecture.py            # Kiểm thử phân lập ranh giới các tầng
│   ├── test_callbacks.py               # Kiểm thử vòng đời các Hook Callbacks
│   ├── test_config.py                  # Kiểm thử phân tích YAML, biến môi trường, validation & override
│   ├── test_dataset.py                 # Kiểm thử DataPipeline & BatchProvider
│   ├── test_diagnostics.py             # Kiểm thử hệ thống chẩn đoán phần cứng & VRAM Estimator
│   ├── test_exceptions.py              # Kiểm thử cây phân cấp ngoại lệ và ErrorCode
│   ├── test_generation.py              # Kiểm thử sinh văn bản, bộ lấy mẫu và streamers
│   ├── test_generation_advanced.py     # Kiểm thử KV-Cache, Repetition Penalty, Min-P sampling
│   ├── test_logging.py                 # Kiểm thử Rich logging & Rotating file handler
│   ├── test_model.py                   # Kiểm thử ModelRegistry, forward pass, shape của Attention/Block
│   ├── test_optimizers.py              # Kiểm thử lịch trình Learning Rate Cosine Warmup & AdamW
│   ├── test_preprocessors.py           # Kiểm thử bộ làm sạch văn bản TextCleaner
│   ├── test_smoke_train.py             # Kiểm thử luồng huấn luyện nhanh, resume checkpoint & loss
│   ├── test_tokenizer.py               # Kiểm thử mã hóa, giải mã CharTokenizer và ByteTokenizer
│   └── test_ui.py                      # Kiểm thử toàn diện API endpoints & Dashboard của Web UI
│
├── main.py                             # CLI duy nhất - Composition Root điều phối toàn bộ hệ thống
└── pyproject.toml                      # Cấu hình Ruff, Pyright, định dạng mã nguồn & metadata dự án
```

---

## ⚡ Các Hệ Thống Bổ Trợ Chuẩn Doanh Nghiệp

### 1. Hệ thống Bắt Lỗi Toàn Diện (Error Handling Hierarchy)

Kế thừa từ `AIEngineError` với định danh mã lỗi (`ErrorCode`) cụ thể:

- `ConfigurationError` / `ConfigValidationError`: Bắt lỗi cấu hình sai lệch hoặc gõ nhầm tham số.
- `HardwareError` / `CudaUnavailableError` / `OutOfMemoryError`: Bắt lỗi thiếu GPU, lỗi driver CUDA, tràn VRAM.
- `DataPipelineError` / `DatasetEmptyError` / `VocabularyMissingError`: Bắt lỗi dữ liệu trống, thiếu từ điển.
- `ModelArchitectureError` / `ModelNotFoundError`: Bắt lỗi không tìm thấy mô hình trong registry, vượt block size.
- `TrainingError` / `TrainingDivergedError`: Tự động ngắt khi phát hiện Loss hoặc Gradient xuất hiện `NaN` hay `Inf`.
- `CheckpointError` / `CheckpointNotFoundError` / `CheckpointCorruptedError`: Bắt lỗi khi không tìm thấy hoặc hỏng file checkpoint.
- `GenerationError` / `SamplingError`: Bắt lỗi trong quá trình lấy mẫu phân phối xác suất.

### 2. Hệ thống Logging Đa Kênh (Dual Logging)

- **Terminal Console**: Sử dụng `RichHandler` hiển thị bảng biểu, màu sắc cảnh báo trực quan theo từng log level.
- **Rotating File**: Tự động ghi vào `logs/engine.log` với `RotatingFileHandler` (giới hạn 10MB/file, xoay vòng 5 bản sao lưu), ghi rõ timestamp, log level, module và dòng code chính xác.

### 3. Hệ thống Debug & Tensor Inspector

- `assert_valid_tensor`: Kiểm tra tính toàn vẹn của tensor ở từng bước forward pass (bắt sớm `NaN`/`Inf`).
- `check_model_gradients`: Quét toàn bộ gradient sau `loss.backward()` để đảm bảo không bị nổ hoặc triệt tiêu gradient.
- `get_cuda_memory_mb`: Giám sát bộ nhớ VRAM phân bổ và đỉnh điểm (Peak VRAM) theo thời gian thực.

### 4. Hệ thống Chẩn Đoán Đa Chiều (System Diagnostics & VRAM Estimator)

- Quét thông số phần cứng (CPU, GPU VRAM, CUDA Compute capability, RAM).
- Phân tích nhân tăng tốc PyTorch SDPA (Cutlass, FlashAttention, Math).
- Đo đạc và dự toán trước ngân sách bộ nhớ VRAM cần thiết theo từng kích thước batch và chiều dài ngữ cảnh (`block_size`).

---

## 🛡️ 6 Cổng Kiểm Soát Chất Lượng (Quality Gates)

Hệ thống được trang bị bộ kiểm toán chất lượng toàn diện kích hoạt qua lệnh `python main.py gate`:

| Chốt Chặn (Gate)         | Công Cụ Kiểm Tra    | Tiêu Chuẩn Đánh Giá                                              | Trạng Thái |
| :----------------------- | :------------------ | :--------------------------------------------------------------- | :--------: |
| **1. Format Gate**       | Ruff Formatter      | 100% tệp tin tuân thủ định dạng PEP 8 chuẩn                      |  ✅ PASS   |
| **2. Lint Gate**         | Ruff Linter         | 0 lỗi cú pháp, 0 biến/import thừa                                |  ✅ PASS   |
| **3. Type Check Gate**   | Pyright (VSCode)    | Phân tích tĩnh nghiêm ngặt: 0 errors, 0 warnings, 0 dead code    |  ✅ PASS   |
| **4. Architecture Gate** | AST Boundary Linter | Khóa cứng ranh giới Clean Architecture, ngăn chặn phụ thuộc chéo |  ✅ PASS   |
| **5. Diagnostics Gate**  | DiagnosticsRunner   | Đảm bảo GPU, VRAM và quyền đọc/ghi ổ đĩa đạt chuẩn HEALTHY       |  ✅ PASS   |
| **6. Test Suite Gate**   | PyTest              | Toàn bộ 14 test suites (128 unit tests) vượt qua 100%            |  ✅ PASS   |

---

## 🚀 Hướng Dẫn Sử Dụng CLI (`main.py`)

File [main.py](main.py) đóng vai trò **Composition Root**, khởi tạo toàn bộ linh kiện từ cấu hình và thực thi các phân hệ:

### 1. Chẩn đoán hệ thống (Health Check)

```powershell
python main.py check
```

### 2. Dự toán ngân sách VRAM theo các kịch bản (Estimate VRAM)

```powershell
# Ước lượng VRAM cho cấu hình hiện tại
python main.py estimate --config configs/truyen_kieu.yaml

# Thử nghiệm với batch size và block size lớn hơn qua cờ --override
python main.py estimate --config configs/truyen_kieu.yaml --override training.batch_size=128 model.block_size=256
```

### 3. Phân tích kiến trúc và tham số mô hình (Inspect)

```powershell
python main.py inspect --config configs/truyen_kieu.yaml
```

### 4. Kiểm toán toàn diện chất lượng (Quality Gates Audit)

```powershell
python main.py gate
```

### 5. Chạy bộ kiểm thử tự động (Unit Tests)

```powershell
pytest tests -v
```

### 6. Huấn luyện mô hình (Train)

```powershell
# Chạy huấn luyện đầy đủ theo cấu hình YAML
python main.py train --config configs/truyen_kieu.yaml

# Huấn luyện thử nghiệm nhanh 50 bước kiểm tra toàn bộ pipeline
python main.py train --config configs/truyen_kieu.yaml --quick-check

# Ghi đè tham số động khi chạy mà không cần sửa file YAML
python main.py train --config configs/truyen_kieu.yaml --override training.learning_rate=0.0005 training.batch_size=32
```

### 7. Sáng tác thơ / Sinh văn bản (Generate)

```powershell
# Chế độ tương tác trực tiếp (Interactive REPL)
python main.py generate

# Sinh văn bản với câu mồi và tham số tùy biến
python main.py generate --prompt "Trăm năm trong cõi người ta," --temp 0.75 --top_k 40 --top_p 0.9 --tokens 250

# Chế độ suy luận Greedy Search xác định
python main.py generate --prompt "Trăm năm" --greedy

# Điều chỉnh hệ số phạt lặp từ (repetition penalty) và Min-P sampling
python main.py generate --prompt "Trăm năm" --repetition_penalty 1.15 --min_p 0.05
```

### 8. Khởi chạy Giao diện Web AI Studio (UI Dashboard)

Trải nghiệm giao diện đồ họa trực quan hiện đại (Single-Page Application) phong cách AI Studio cao cấp:

```powershell
# Khởi chạy giao diện tại địa chỉ http://127.0.0.1:8000
python main.py ui

# Tùy chỉnh cổng và bật tự động nạp lại khi lập trình
python main.py ui --port 8080 --reload
```

Giao diện tích hợp sẵn 4 phân hệ:

1. **✍️ Sáng Tác (Playground)**: Nhập prompt thơ, streaming token thời gian thực (SSE typewriter effect), tinh chỉnh Temperature, Top-K, Top-P, Min-P, Repetition Penalty, đo tốc độ Tokens/giây (TPS).
2. **📊 Huấn Luyện (Training Studio)**: Điều khiển Start/Stop, biểu đồ hội tụ Loss thời gian thực (Live Loss Curves với Chart.js), bản xem trước văn bản mẫu sinh thử nghiệm định kỳ.
3. **🖥️ Phần Cứng & VRAM (Diagnostics)**: Theo dõi CPU, RAM, GPU GTX 1660 SUPER VRAM, bộ giả lập VRAM (VRAM Budget Estimator) chống tràn bộ nhớ.
4. **🔬 Dữ Liệu & Tokenizer (Explorer)**: Trực quan hóa Token IDs dạng chip màu sắc, xem mẫu văn bản gốc và thống kê từ vựng.

---

## 🧩 Khả Năng Mở Rộng Hệ Thống (Extensibility)

Nhờ áp dụng Factory Pattern và Registry Decorator, việc mở rộng tính năng không bao giờ yêu cầu sửa đổi code lõi:

### Thêm một kiến trúc Mô hình mới:

1. Tạo file trong `src/models/architectures/my_model.py`.
2. Đăng ký vào registry:

    ```python
    from src.core.config import ModelConfig
    from src.models.base import BaseModel
    from src.models.registry import ModelRegistry


    @ModelRegistry.register("my_model")
    class MyModel(BaseModel):
        def __init__(self, config: ModelConfig):
            super().__init__()
            ...
    ```

3. Đổi `model.name: "my_model"` trong file cấu hình YAML.

### Thêm một Callback huấn luyện mới:

1. Kế thừa `BaseCallback` trong `src/training/callbacks/`:

    ```python
    from src.training.callbacks.base import BaseCallback, TrainerProtocol


    class CustomMetricsCallback(BaseCallback):
        def on_step_end(self, trainer: TrainerProtocol, step: int, loss: float) -> None:
            print(f"Step {step}: Loss = {loss:.4f}, LR = {trainer.current_lr:.6f}")
    ```

2. Truyền vào danh sách `callbacks` trong Composition Root.

### Thêm một Tokenizer hoặc Cleaner mới:

- Kế thừa `BaseTokenizer` và đăng ký `@TokenizerRegistry.register("my_tok")`.
- Kế thừa `BaseCleaner` và đăng ký `@CleanerRegistry.register("my_cleaner")`.
