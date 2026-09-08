"""
Kiểm thử tự động cho phân hệ UI (FastAPI AI Studio Dashboard).
"""

import pytest
from fastapi.testclient import TestClient

from src.ui.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_ui_healthz(client: TestClient):
    """Kiểm tra endpoint /healthz phản hồi 200 OK."""
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "ai-studio"}


def test_ui_index_html(client: TestClient):
    """Kiểm tra trang chủ index.html được render thành công."""
    res = client.get("/")
    assert res.status_code == 200
    assert "AI Studio" in res.text
    assert "Sáng Tác" in res.text


def test_ui_diagnostics_system(client: TestClient):
    """Kiểm tra endpoint chẩn đoán hệ thống."""
    res = client.get("/api/diagnostics/system")
    assert res.status_code == 200
    data = res.json()
    assert "cpu" in data
    assert "memory" in data
    assert "gpu" in data
    assert "system" in data


def test_ui_diagnostics_estimate(client: TestClient):
    """Kiểm tra endpoint tính toán ngân sách VRAM."""
    payload = {
        "batch_size": 32,
        "block_size": 64,
        "n_embd": 128,
        "n_layer": 2,
        "n_head": 4,
        "vocab_size": 129,
        "precision": "float32",
    }
    res = client.post("/api/diagnostics/estimate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "peak_vram_mb" in data
    assert "model_weights_mb" in data
    assert data["peak_vram_mb"] > 0


def test_ui_checkpoints_list(client: TestClient):
    """Kiểm tra endpoint danh sách checkpoints."""
    res = client.get("/api/checkpoints")
    assert res.status_code == 200
    data = res.json()
    assert "checkpoints" in data
    assert isinstance(data["checkpoints"], list)


def test_ui_explorer_tokenize(client: TestClient):
    """Kiểm tra endpoint trực quan hóa Tokenizer."""
    payload = {"text": "Trăm năm"}
    res = client.post("/api/explorer/tokenize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["text"] == "Trăm năm"
    assert "token_ids" in data
    assert "tokens" in data
    assert len(data["token_ids"]) == len(data["tokens"])


def test_ui_explorer_dataset_sample(client: TestClient):
    """Kiểm tra endpoint xem mẫu dữ liệu."""
    res = client.get("/api/explorer/dataset-sample")
    assert res.status_code == 200
    data = res.json()
    assert "total_lines" in data
    assert "sample_lines" in data


def test_ui_training_status(client: TestClient):
    """Kiểm tra endpoint lấy trạng thái huấn luyện."""
    res = client.get("/api/training/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] in ["IDLE", "RUNNING", "COMPLETED", "STOPPED"]


def test_ui_diagnostics_scenarios(client: TestClient):
    """Kiểm tra endpoint so sánh 4 kịch bản VRAM."""
    payload = {
        "batch_size": 32,
        "block_size": 64,
        "n_embd": 128,
        "n_layer": 2,
        "n_head": 4,
        "vocab_size": 129,
    }
    res = client.post("/api/diagnostics/scenarios", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) == 4
    assert "recommended" in data
    for sc in data["scenarios"]:
        assert "estimated_gb" in sc
        assert "feasible" in sc


def test_ui_diagnostics_inspect(client: TestClient):
    """Kiểm tra endpoint soi cấu trúc mô hình."""
    res = client.get("/api/diagnostics/inspect")
    assert res.status_code == 200
    data = res.json()
    assert "model_name" in data
    assert "total_parameters" in data
    assert "layers" in data
    assert len(data["layers"]) > 0


def test_ui_explorer_tokenize_byte(client: TestClient):
    """Kiểm tra endpoint trực quan hóa ByteTokenizer."""
    payload = {"text": "Trăm năm", "tokenizer_type": "byte"}
    res = client.post("/api/explorer/tokenize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tokenizer_type"] == "byte"
    assert "token_ids" in data
    assert len(data["token_ids"]) > 0


def test_ui_explorer_clean(client: TestClient):
    """Kiểm tra endpoint làm sạch văn bản TextCleaner."""
    payload = {"text": "1.   Trăm năm trong   cõi người ta  ,\n", "clean_line_numbers": True}
    res = client.post("/api/explorer/clean", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "cleaned" in data
    assert data["cleaned"].startswith("Trăm năm")
    assert data["diff_chars"] > 0


def test_ui_checkpoints_delete(client: TestClient):
    """Kiểm tra endpoint xóa checkpoint an toàn."""
    import os

    import torch

    os.makedirs("checkpoints", exist_ok=True)
    dummy_path = os.path.join("checkpoints", "dummy_delete_test.pt")
    torch.save({"step": 1, "dummy": True}, dummy_path)
    assert os.path.exists(dummy_path)

    # Xóa thành công
    res = client.delete("/api/checkpoints/dummy_delete_test.pt")
    assert res.status_code == 200
    assert not os.path.exists(dummy_path)

    # Xóa file không tồn tại -> 404
    res_404 = client.delete("/api/checkpoints/non_existent_file.pt")
    assert res_404.status_code == 404


def test_ui_diagnostics_advisor(client: TestClient):
    """Kiểm tra endpoint cố vấn phần cứng và kiểm toán lưu trữ."""
    res = client.get("/api/diagnostics/advisor")
    assert res.status_code == 200
    data = res.json()
    assert "gpu" in data
    assert "backends" in data
    assert "disk" in data
    assert "permissions" in data
    assert "recommendations" in data
    assert "math_attention" in data["backends"]
    assert "logs" in data["permissions"]
    assert "health_status" in data
    assert "warnings" in data
    assert "suggestions" in data


def test_ui_diagnostics_inspect_llama(client: TestClient):
    """Kiểm tra endpoint soi cấu trúc mô hình LLaMA Nano."""
    res = client.get("/api/diagnostics/inspect?model_name=llama")
    assert res.status_code == 200
    data = res.json()
    assert data["model_name"] == "llama"
    assert data["total_parameters"] > 0
    assert len(data["layers"]) > 0


def test_ui_diagnostics_logs(client: TestClient):
    """Kiểm tra endpoint đọc nhật ký hệ thống."""
    res = client.get("/api/diagnostics/logs?lines=20")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "file" in data
    assert isinstance(data["logs"], list)
    assert data["total_lines"] >= 0


def test_ui_explorer_tokenize_gemini(client: TestClient):
    """Kiểm tra trực quan hóa Gemini AI Tokenizer (với Zero-OOV Fallback)."""
    payload = {"text": "Trăm năm Kiều", "tokenizer_type": "gemini"}
    res = client.post("/api/explorer/tokenize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tokenizer_type"] == "gemini"
    assert len(data["token_ids"]) > 0


def test_ui_explorer_clean_advanced(client: TestClient):
    """Kiểm tra các bộ lọc chất lượng văn bản nâng cao (dedup, repetition, line length)."""
    payload = {
        "text": "1.   Câu thơ số một....\n2.   Câu thơ số hai!!!!\n3.   Câu thơ số hai!!!!\n4. x\n",
        "clean_line_numbers": True,
        "dedup": True,
        "repetition": True,
        "min_length": 3,
        "max_length": 100,
    }
    res = client.post("/api/explorer/clean", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "cleaned" in data
    lines = data["cleaned"].splitlines()
    assert (
        len(lines) == 2
    )  # dòng 3 bị dedup, dòng 4 'x' bị min_length lọc, '....' & '!!!!' bị repetition nén


def test_ui_explorer_export_binary(client: TestClient):
    """Kiểm tra đóng gói dữ liệu nhị phân (.bin) cho Memmap loader."""
    res = client.post("/api/explorer/export-binary")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["train_tokens"] > 0
    assert data["val_tokens"] > 0
    assert data["train_size_mb"] >= 0


def test_ui_training_start_with_hyperparameters(client: TestClient):
    """Kiểm tra bắt đầu huấn luyện với kiến trúc LLaMA và siêu tham số nâng cao."""
    payload = {
        "quick_check": True,
        "model_name": "llama",
        "lr_scheduler_type": "cosine",
        "warmup_iters": 10,
        "min_lr": 1e-5,
        "weight_decay": 0.01,
        "grad_clip": 0.5,
        "early_stopping_patience": 5,
    }
    res = client.post("/api/training/start", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    # Dừng lại ngay để không tốn tài nguyên
    stop_res = client.post("/api/training/stop")
    assert stop_res.status_code == 200


def test_ui_generators(client: TestClient):
    """Kiểm tra liệt kê và lựa chọn Generator Backend."""
    res = client.get("/api/generators")
    assert res.status_code == 200
    data = res.json()
    assert "generators" in data
    assert "current_backend" in data
    assert "local" in data["generators"]

    # Chọn backend hợp lệ
    res_select = client.post("/api/generators/select", json={"backend": "local"})
    assert res_select.status_code == 200
    assert res_select.json()["status"] == "success"

    # Chọn backend không tồn tại -> 400
    res_invalid = client.post("/api/generators/select", json={"backend": "invalid_backend_xyz"})
    assert res_invalid.status_code == 400


def test_ui_check_feasibility(client: TestClient):
    """Kiểm tra tiền kiểm toán bộ nhớ VRAM trước khi huấn luyện."""
    payload = {
        "batch_size": 32,
        "n_embd": 128,
        "n_layer": 2,
        "n_head": 4,
    }
    res = client.post("/api/training/check-feasibility", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "feasible" in data
    assert "estimated_gb" in data
    assert "estimated_mb" in data


def test_ui_compare_tokenizers(client: TestClient):
    """Kiểm tra so sánh đồng thời 3 bộ mã hóa Char, Byte và Gemini."""
    payload = {"text": "Trăm năm trong cõi người ta"}
    res = client.post("/api/explorer/compare-tokenizers", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "comparisons" in data
    assert "byte" in data["comparisons"]
    assert "gemini" in data["comparisons"]
    assert data["comparisons"]["byte"]["token_count"] > 0


def test_ui_diagnostics_gates_run(client: TestClient):
    """Kiểm tra kích hoạt 6 Quality Gates qua API chẩn đoán."""
    from unittest.mock import patch

    dummy_result = {"name": "Gate", "passed": True, "elapsed": 0.05, "details": "OK"}
    with (
        patch("scripts.check_all.run_format_gate", return_value=dummy_result),
        patch("scripts.check_all.run_lint_gate", return_value=dummy_result),
        patch("scripts.check_all.run_type_gate", return_value=dummy_result),
        patch("scripts.check_all.run_architecture_gate", return_value=dummy_result),
        patch("scripts.check_all.run_diagnostics_gate", return_value=dummy_result),
        patch("scripts.check_all.run_test_suite_gate", return_value=dummy_result),
    ):
        res = client.post("/api/diagnostics/gates/run")
        assert res.status_code == 200
        data = res.json()
        assert data["all_passed"] is True
        assert len(data["results"]) == 6


def test_ui_checkpoint_download(client: TestClient):
    """Kiểm tra tải file checkpoint về máy qua API."""
    import os

    import torch

    os.makedirs("checkpoints", exist_ok=True)
    test_file = os.path.join("checkpoints", "test_download_file.pt")
    torch.save({"dummy": 123}, test_file)
    try:
        res = client.get("/api/checkpoints/test_download_file.pt/download")
        assert res.status_code == 200
        assert len(res.content) > 0

        res_404 = client.get("/api/checkpoints/non_existent_model.pt/download")
        assert res_404.status_code == 404
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_ui_models(client: TestClient):
    """Kiểm tra liệt kê các kiến trúc mô hình đã đăng ký."""
    res = client.get("/api/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "minigpt" in data["models"]
    assert "llama" in data["models"]


def test_ui_configs_raw_and_save(client: TestClient):
    """Kiểm tra đọc và lưu cấu hình YAML an toàn."""
    import os

    # Đọc file hợp lệ
    res = client.get("/api/configs/raw?path=configs/truyen_kieu.yaml")
    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    assert "system:" in data["content"]

    # Đọc file ngoài thư mục configs -> 400
    res_bad = client.get("/api/configs/raw?path=main.py")
    assert res_bad.status_code == 400

    # Lưu file YAML hợp lệ
    temp_yaml = "configs/test_temp_config.yaml"
    try:
        save_res = client.post(
            "/api/configs/save",
            json={"path": temp_yaml, "content": "system:\n  seed: 42\n"},
        )
        assert save_res.status_code == 200
        assert os.path.exists(temp_yaml)

        # Lưu cú pháp YAML lỗi -> 400
        bad_save = client.post(
            "/api/configs/save",
            json={"path": temp_yaml, "content": "system: [unclosed bracket"},
        )
        assert bad_save.status_code == 400
    finally:
        if os.path.exists(temp_yaml):
            os.remove(temp_yaml)


def test_ui_training_with_block_size_and_seed(client: TestClient):
    """Kiểm tra khởi chạy huấn luyện với block_size và seed tùy biến."""
    payload = {
        "quick_check": True,
        "block_size": 64,
        "seed": 9999,
        "n_layer": 2,
        "n_embd": 128,
        "n_head": 4,
    }
    # Feasibility check
    feasibility_res = client.post("/api/training/check-feasibility", json=payload)
    assert feasibility_res.status_code == 200
    assert feasibility_res.json()["feasible"] is True

    # Đảm bảo phiên huấn luyện trước đã dừng hoàn toàn
    client.post("/api/training/stop")
    import time

    time.sleep(0.1)

    # Khởi chạy training
    res = client.post("/api/training/start", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # Dừng training
    client.post("/api/training/stop")


def test_ui_training_clear(client: TestClient):
    """Kiểm tra endpoint xóa thông tin huấn luyện /api/training/clear."""
    res = client.post("/api/training/clear")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    # Kiểm tra trạng thái đã trở về IDLE và rỗng
    status_res = client.get("/api/training/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "IDLE"
    assert status_data["current_step"] == 0
    assert status_data["current_loss"] is None
    assert len(status_data["history_steps"]) == 0


def test_ui_training_start_with_resume_checkpoint(client: TestClient):
    """Kiểm tra validation file resume checkpoint tồn tại và không tồn tại."""
    # 1. File không tồn tại -> 400
    bad_res = client.post(
        "/api/training/start",
        json={"resume_checkpoint": "checkpoints/definitely_not_exist_xyz.pt"},
    )
    assert bad_res.status_code == 400
    assert "Không tìm thấy file checkpoint để resume" in bad_res.json()["detail"]

    # 2. File tồn tại hợp lệ -> 200 (nếu có best_model.pt)
    import os

    if os.path.exists("checkpoints/best_model.pt"):
        client.post("/api/training/stop")
        import time

        time.sleep(0.1)
        valid_res = client.post(
            "/api/training/start",
            json={
                "quick_check": True,
                "resume_checkpoint": "checkpoints/best_model.pt",
            },
        )
        assert valid_res.status_code == 200
        client.post("/api/training/stop")


def test_ui_configs_reject_lookalike_directory(client: TestClient):
    """Config API must not escape the real configs/ directory via prefix lookalikes."""
    import os

    os.makedirs("configs_evil", exist_ok=True)
    leak_path = "configs_evil/leak.yaml"
    write_path = "configs_evil/written.yaml"
    try:
        with open(leak_path, "w", encoding="utf-8") as f:
            f.write("secret: 123\n")

        read_res = client.get("/api/configs/raw", params={"path": leak_path})
        assert read_res.status_code == 400

        write_res = client.post(
            "/api/configs/save",
            json={"path": write_path, "content": "x: 1\n"},
        )
        assert write_res.status_code == 400
        assert not os.path.exists(write_path)
    finally:
        for path in (leak_path, write_path):
            if os.path.exists(path):
                os.remove(path)
        if os.path.isdir("configs_evil") and not os.listdir("configs_evil"):
            os.rmdir("configs_evil")


def test_ui_generate_stream_rejects_invalid_backend_before_streaming(client: TestClient):
    """Invalid backend must fail as a normal 400 response, not inside the SSE iterator."""
    res = client.post(
        "/api/generate/stream",
        json={"prompt": "hello world", "backend": "invalid_backend_xyz"},
    )
    assert res.status_code == 400


def test_ui_training_start_rejects_invalid_config_before_background_start(client: TestClient):
    """Invalid training overrides must be returned as a client error, not escape FastAPI."""
    res = client.post(
        "/api/training/start",
        json={"run_name": "../escape", "eval_iters": 0},
    )
    assert res.status_code == 400


def test_ui_training_feasibility_rejects_invalid_config_as_client_error(client: TestClient):
    res = client.post(
        "/api/training/check-feasibility",
        json={"config_path": "configs/definitely_missing_config_xyz.yaml"},
    )
    assert res.status_code == 400


def test_ui_checkpoint_load_missing_file_is_404(client: TestClient):
    res = client.post(
        "/api/checkpoints/load",
        json={"path": "checkpoints/definitely_missing_load_xyz.pt"},
    )
    assert res.status_code == 404


def test_ui_checkpoint_load_invalid_backend_is_400(client: TestClient):
    res = client.post(
        "/api/checkpoints/load",
        json={
            "path": "checkpoints/definitely_missing_load_xyz.pt",
            "backend": "invalid_backend_xyz",
        },
    )
    assert res.status_code == 400
