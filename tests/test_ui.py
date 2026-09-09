"""
Kiểm thử tự động cho phân hệ UI (FastAPI AI Studio Dashboard).
"""

from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.ui.app import create_app


def _app_state(client: TestClient):
    return cast(FastAPI, client.app).state


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
    """Alias tokenizer legacy ``gemini`` vẫn tương thích với ByteTokenizer."""
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
    invalid_payload = res_invalid.json()
    assert invalid_payload["error_code"] == "ERR_GEN_BACKEND_NOT_FOUND"
    assert invalid_payload["is_recoverable"] is True


def test_training_start_reuses_preflight_runtime_plan_for_worker() -> None:
    from unittest.mock import Mock, patch

    from src.core.config import EngineConfig
    from src.core.runtime import RuntimeCapabilities, resolve_training_plan

    config = EngineConfig()
    config = config.copy(system=config.system.copy(device="cpu"))
    runtime_plan = resolve_training_plan(
        config,
        capabilities=RuntimeCapabilities(
            cuda_available=False,
            mps_available=False,
            bf16_supported=False,
            bitsandbytes_available=False,
        ),
    )
    app = create_app()
    start_training_mock = Mock()
    app.state.services.training._background.start_training = start_training_mock

    with (
        patch(
            "src.application.training.service.resolve_training_plan", return_value=runtime_plan
        ) as resolve_mock,
        TestClient(app) as local_client,
    ):
        response = local_client.post(
            "/api/training/start",
            json={"run_name": "runtime_plan_test"},
        )

    assert response.status_code == 200
    resolve_mock.assert_called_once()
    started_plan = start_training_mock.call_args.kwargs["plan"]
    assert started_plan.runtime_plan is runtime_plan
    assert started_plan.requested_config.training.run_name == "runtime_plan_test"


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
    assert data["advisory"] is True


def test_ui_compare_tokenizers(client: TestClient):
    """Chỉ so sánh các tokenizer có semantics khác nhau, không lặp alias Gemini."""
    payload = {"text": "Trăm năm trong cõi người ta"}
    res = client.post("/api/explorer/compare-tokenizers", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "comparisons" in data
    assert "byte" in data["comparisons"]
    assert "gemini" not in data["comparisons"]
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
    payload = res.json()
    assert payload["error_code"] == "ERR_GEN_BACKEND_NOT_FOUND"
    assert payload["details"]["requested"] == "invalid_backend_xyz"


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


def test_ui_stop_words_preserve_multi_token_sequences(client: TestClient, monkeypatch):
    service = _app_state(client).services.inference._service
    captured = {}

    class FakeSession:
        def iter_events(self):
            yield {
                "type": "done",
                "generated_text": "",
                "full_text": "c",
                "token_count": 0,
                "elapsed_sec": 0.0,
                "tps": 0.0,
            }

        def close(self):
            pass

    def fake_begin(prompt, config, backend=None, stop_words=None):
        captured["config"] = config
        captured["stop_words"] = stop_words
        return FakeSession()

    monkeypatch.setattr(service, "begin_generation", fake_begin)
    response = client.post(
        "/api/generate/stream",
        json={"prompt": "c", "max_new_tokens": 10, "stop_words": ["ab"]},
    )

    assert response.status_code == 200
    assert captured["stop_words"] == ["ab"]
    assert captured["config"].stop_sequences is None


def test_ui_checkpoint_download_uses_inference_service_directory(client: TestClient, tmp_path):
    import torch

    service = _app_state(client).services.inference._service
    old_dir = service.checkpoint_dir
    custom_dir = tmp_path / "custom-checkpoints"
    custom_dir.mkdir()
    torch.save({"step": 1}, custom_dir / "custom.pt")
    service.checkpoint_dir = str(custom_dir)
    try:
        response = client.get("/api/checkpoints/custom.pt/download")
    finally:
        service.checkpoint_dir = old_dir

    assert response.status_code == 200
    assert response.content


def test_ui_training_feasibility_does_not_silently_ignore_zero_override(client: TestClient):
    res = client.post("/api/training/check-feasibility", json={"batch_size": 0})
    assert res.status_code == 400


def test_ui_training_start_commits_inference_checkpoint_dir_only_after_start_succeeds(
    client: TestClient, monkeypatch
):
    training_service = _app_state(client).services.training
    inference_service = _app_state(client).services.inference._service
    committed_dirs = []

    def reject_start(*args, **kwargs):
        raise RuntimeError("already running")

    monkeypatch.setattr(training_service._background, "start_training", reject_start)
    monkeypatch.setattr(
        inference_service, "set_checkpoint_dir", lambda path: committed_dirs.append(path)
    )

    res = client.post("/api/training/start", json={"quick_check": True})

    assert res.status_code == 400
    assert committed_dirs == []


def test_ui_checkpoint_download_rejects_symlink_escape(client: TestClient, tmp_path):
    import os

    import torch

    if not hasattr(os, "symlink"):
        pytest.skip("symlink unavailable")

    service = _app_state(client).services.inference._service
    old_dir = service.checkpoint_dir
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    outside = tmp_path / "outside.pt"
    torch.save({"step": 99}, outside)
    link = checkpoint_dir / "escape.pt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")

    service.checkpoint_dir = str(checkpoint_dir)
    try:
        response = client.get("/api/checkpoints/escape.pt/download")
    finally:
        service.checkpoint_dir = old_dir

    assert response.status_code in {400, 404}


def test_ui_config_read_rejects_symlink_escape(client: TestClient, tmp_path, monkeypatch):
    import os

    if not hasattr(os, "symlink"):
        pytest.skip("symlink unavailable")

    configs = tmp_path / "configs"
    configs.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("secret: true\n", encoding="utf-8")
    link = configs / "escape.yaml"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation unavailable")

    monkeypatch.chdir(tmp_path)
    response = client.get("/api/configs/raw", params={"path": "configs/escape.yaml"})

    assert response.status_code == 400


def test_ui_byte_tokenizer_visualizer_does_not_render_utf8_bytes_as_replacement_chars(
    client: TestClient,
):
    response = client.post(
        "/api/explorer/tokenize",
        json={"text": "ă", "tokenizer_type": "byte"},
    )

    assert response.status_code == 200
    raw = [item["raw"] for item in response.json()["tokens"]]
    assert raw == ["0xC4", "0x83"]
    assert "�" not in "".join(raw)


def test_ui_config_save_rejects_semantically_invalid_yaml_without_overwriting(
    client: TestClient, tmp_path, monkeypatch
):
    configs = tmp_path / "configs"
    configs.mkdir()
    target = configs / "semantic.yaml"
    original = "model:\n  n_embd: 96\n  n_head: 6\n"
    target.write_text(original, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    response = client.post(
        "/api/configs/save",
        json={
            "path": "configs/semantic.yaml",
            "content": "model:\n  n_embd: 100\n  n_head: 6\n",
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "ERR_CFG_INVALID"
    assert payload["error_type"] == "ConfigurationError"
    assert payload["suggestion"]
    assert target.read_text(encoding="utf-8") == original


def test_ui_config_save_uses_atomic_replace(client: TestClient, tmp_path, monkeypatch):
    import src.ui.routes.inference as inference_routes

    configs = tmp_path / "configs"
    configs.mkdir()
    target = configs / "atomic.yaml"
    target.write_text("system:\n  seed: 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    real_replace = inference_routes.os.replace
    calls = []

    def tracking_replace(source: str, destination: str) -> None:
        calls.append((source, destination))
        real_replace(source, destination)

    monkeypatch.setattr(inference_routes.os, "replace", tracking_replace)

    response = client.post(
        "/api/configs/save",
        json={"path": "configs/atomic.yaml", "content": "system:\n  seed: 42\n"},
    )

    assert response.status_code == 200
    assert calls
    assert calls[-1][1] == str(target.resolve())
    assert target.read_text(encoding="utf-8") == "system:\n  seed: 42\n"


def test_ui_diagnostics_estimate_honors_llama_memory_profile(client: TestClient):
    response = client.post(
        "/api/diagnostics/estimate",
        json={
            "model_name": "llama",
            "batch_size": 4,
            "block_size": 64,
            "n_embd": 96,
            "n_layer": 2,
            "n_head": 6,
            "vocab_size": 257,
            "intermediate_size": 1024,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "llama"
    assert data["total_parameters"] == 688_704


def test_training_start_accepts_canonical_dotted_overrides_without_schema_copy():
    from unittest.mock import Mock, patch

    from src.core.config import EngineConfig
    from src.core.runtime import RuntimeCapabilities, resolve_training_plan
    from src.ui.app import create_app

    config = EngineConfig().copy(system=EngineConfig().system.copy(device="cpu"))
    runtime_plan = resolve_training_plan(
        config,
        capabilities=RuntimeCapabilities(
            cuda_available=False,
            mps_available=False,
            bf16_supported=False,
            bitsandbytes_available=False,
        ),
    )
    app = create_app()
    start_mock = Mock()
    app.state.services.training._background.start_training = start_mock

    with (
        patch("src.application.training.service.resolve_training_plan", return_value=runtime_plan),
        TestClient(app) as local_client,
    ):
        response = local_client.post(
            "/api/training/start",
            json={
                "overrides": {
                    "training.optimizer_type": "sgd",
                    "training.batch_size": 7,
                    "model.n_layer": 3,
                },
                "run_name": "compat_name",
            },
        )

    assert response.status_code == 200
    started_plan = start_mock.call_args.kwargs["plan"]
    assert started_plan.requested_config.training.optimizer_type == "sgd"
    assert started_plan.requested_config.training.batch_size == 7
    assert started_plan.requested_config.model.n_layer == 3
    # Legacy top-level fields are normalized before the application boundary.
    assert started_plan.requested_config.training.run_name == "compat_name"


def test_training_start_rejects_unknown_canonical_override_key_before_worker_start():
    from unittest.mock import Mock

    from src.ui.app import create_app

    app = create_app()
    start_mock = Mock()
    app.state.services.training._background.start_training = start_mock

    with TestClient(app) as local_client:
        response = local_client.post(
            "/api/training/start",
            json={"overrides": {"training.typo_learning_rate": 0.1}},
        )

    assert response.status_code == 400
    start_mock.assert_not_called()


def test_training_config_endpoint_exposes_canonical_engine_config(client: TestClient):
    response = client.get(
        "/api/training/config",
        params={"path": "configs/truyen_kieu.yaml"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"]["name"] in {"minigpt", "llama", "llama_nano"}
    assert payload["training"]["optimizer_type"] in {"adamw", "8bit_adamw", "sgd"}
    assert isinstance(payload["training"]["batch_size"], int)


def test_training_start_rejects_unknown_legacy_top_level_override(client: TestClient):
    response = client.post(
        "/api/training/start",
        json={"learning_rtae": 0.01},
    )

    assert response.status_code == 400
    assert "learning_rtae" in response.json()["detail"]


def test_ui_training_config_endpoint_rejects_path_escape(client: TestClient):
    response = client.get("/api/training/config", params={"path": "../pyproject.toml"})
    assert response.status_code == 400
    payload = response.json()
    assert "configs" in payload.get("detail", payload.get("message", ""))


def test_ui_training_feasibility_rejects_config_path_escape(client: TestClient):
    response = client.post(
        "/api/training/check-feasibility",
        json={"config_path": "../pyproject.toml"},
    )
    assert response.status_code == 400
    payload = response.json()
    assert "configs" in payload.get("detail", payload.get("message", ""))


def test_ui_training_resume_rejects_checkpoint_outside_configured_dir(
    client: TestClient, tmp_path, monkeypatch
):
    outside = tmp_path / "outside.pt"
    outside.write_bytes(b"checkpoint")
    training_service = _app_state(client).services.training
    start_calls = []
    monkeypatch.setattr(
        training_service._background,
        "start_training",
        lambda *args, **kwargs: start_calls.append((args, kwargs)),
    )

    response = client.post(
        "/api/training/start",
        json={"resume_checkpoint": str(outside)},
    )

    assert response.status_code == 400
    assert "checkpoint_dir" in response.json()["detail"]
    assert start_calls == []


def test_ui_generate_accepts_zero_top_k_as_disabled_filter(client: TestClient, monkeypatch):
    service = _app_state(client).services.inference._service

    class FakeSession:
        def iter_events(self):
            yield {
                "type": "done",
                "generated_text": "",
                "full_text": "x",
                "token_count": 0,
                "elapsed_sec": 0.0,
                "tps": 0.0,
            }

        def close(self):
            pass

    captured = {}

    def fake_begin(prompt, config, backend=None, stop_words=None):
        captured["config"] = config
        return FakeSession()

    monkeypatch.setattr(service, "begin_generation", fake_begin, raising=False)
    response = client.post(
        "/api/generate/stream",
        json={"prompt": "x", "top_k": 0, "top_p": 0.0, "max_new_tokens": 1},
    )

    assert response.status_code == 200
    assert captured["config"].top_k == 0
    assert captured["config"].top_p == 0.0


def test_ui_generation_busy_is_rejected_before_sse_response(client: TestClient, monkeypatch):
    from src.core.exceptions import GenerationBusyError

    service = _app_state(client).services.inference._service

    def busy(*args, **kwargs):
        raise GenerationBusyError(active=2, limit=2)

    monkeypatch.setattr(service, "begin_generation", busy, raising=False)
    response = client.post(
        "/api/generate/stream",
        json={"prompt": "x", "max_new_tokens": 1},
    )

    assert response.status_code == 429
    assert response.json()["error_code"] == "ERR_GEN_BUSY"


def test_ui_generate_rejects_too_many_stop_words_before_service(client: TestClient, monkeypatch):
    service = _app_state(client).services.inference._service
    calls = []
    monkeypatch.setattr(
        service,
        "begin_generation",
        lambda *args, **kwargs: calls.append((args, kwargs)),
        raising=False,
    )

    response = client.post(
        "/api/generate/stream",
        json={"prompt": "x", "stop_words": ["stop"] * 65, "max_new_tokens": 1},
    )

    assert response.status_code == 422
    assert calls == []


def test_ui_generate_rejects_oversized_stop_word_before_service(client: TestClient, monkeypatch):
    service = _app_state(client).services.inference._service
    calls = []
    monkeypatch.setattr(
        service,
        "begin_generation",
        lambda *args, **kwargs: calls.append((args, kwargs)),
        raising=False,
    )

    response = client.post(
        "/api/generate/stream",
        json={"prompt": "x", "stop_words": ["s" * 257], "max_new_tokens": 1},
    )

    assert response.status_code == 422
    assert calls == []


def test_training_start_preserves_run_name_from_resolved_yaml(tmp_path, monkeypatch):
    from unittest.mock import Mock

    from src.ui.app import create_app

    monkeypatch.chdir(tmp_path)
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "custom.yaml").write_text(
        "system:\n  device: cpu\ntraining:\n  run_name: yaml_run\n",
        encoding="utf-8",
    )

    app = create_app()
    start_mock = Mock()
    app.state.services.training._background.start_training = start_mock

    with TestClient(app) as local_client:
        response = local_client.post(
            "/api/training/start",
            json={"config_path": "configs/custom.yaml"},
        )

    assert response.status_code == 200
    started_plan = start_mock.call_args.kwargs["plan"]
    assert started_plan.requested_config.training.run_name == "yaml_run"


def test_create_app_bootstraps_inference_from_canonical_engine_config(tmp_path, monkeypatch):
    from src.ui.app import create_app

    monkeypatch.chdir(tmp_path)
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "truyen_kieu.yaml").write_text(
        "system:\n  device: cpu\n"
        "data:\n  vocab_file: custom/vocab.json\n"
        "training:\n  checkpoint_dir: custom/checkpoints\n  checkpoint_name: champion.pt\n"
        "generation:\n  temperature: 0.23\n  max_new_tokens: 77\n",
        encoding="utf-8",
    )

    app = create_app()
    service = app.state.services.inference._service

    assert service.checkpoint_dir == "custom/checkpoints"
    assert service.checkpoint_name == "champion.pt"
    assert service.vocab_path == "custom/vocab.json"
    assert service.default_generation_config.temperature == 0.23
    assert service.default_generation_config.max_new_tokens == 77


def test_config_save_updates_inference_preferences_and_state_endpoint(tmp_path, monkeypatch):
    from src.ui.app import create_app

    monkeypatch.chdir(tmp_path)
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "truyen_kieu.yaml").write_text("system:\n  device: cpu\n", encoding="utf-8")
    app = create_app()

    content = (
        "system:\n  device: cpu\n"
        "data:\n  vocab_file: data/new-vocab.json\n"
        "training:\n  checkpoint_dir: runs/checkpoints\n  checkpoint_name: chosen.pt\n"
        "generation:\n  temperature: 0.31\n  top_k: 7\n"
    )
    with TestClient(app) as local_client:
        saved = local_client.post(
            "/api/configs/save",
            json={"path": "configs/truyen_kieu.yaml", "content": content},
        )
        state = local_client.get("/api/inference/state")

    assert saved.status_code == 200
    assert state.status_code == 200
    payload = state.json()
    assert payload["checkpoint_dir"] == "runs/checkpoints"
    assert payload["checkpoint_name"] == "chosen.pt"
    assert payload["vocab_path"] == "data/new-vocab.json"
    assert payload["generation"]["temperature"] == 0.31
    assert payload["generation"]["top_k"] == 7


def test_ui_generate_omitted_sampling_fields_inherit_canonical_generation_config(
    client: TestClient, monkeypatch
):
    from src.core.config import GenerationConfig

    service = _app_state(client).services.inference._service
    service.default_generation_config = GenerationConfig(
        max_new_tokens=77,
        temperature=0.23,
        top_k=7,
        top_p=0.81,
        min_p=0.12,
        repetition_penalty=1.17,
        do_sample=False,
        use_cache=False,
    )
    captured = {}

    class FakeSession:
        def iter_events(self):
            yield {
                "type": "done",
                "generated_text": "",
                "full_text": "x",
                "token_count": 0,
                "elapsed_sec": 0.0,
                "tps": 0.0,
            }

        def close(self):
            pass

    def fake_begin(prompt, config, backend=None, stop_words=None):
        captured["config"] = config
        return FakeSession()

    monkeypatch.setattr(service, "begin_generation", fake_begin)
    response = client.post("/api/generate/stream", json={"prompt": "x"})

    assert response.status_code == 200
    config = captured["config"]
    assert config.max_new_tokens == 77
    assert config.temperature == 0.23
    assert config.top_k == 7
    assert config.top_p == 0.81
    assert config.min_p == 0.12
    assert config.repetition_penalty == 1.17
    assert config.do_sample is False
    assert config.use_cache is False


def test_explorer_dataset_sample_uses_requested_canonical_config(tmp_path, monkeypatch):
    import json

    from fastapi.testclient import TestClient as LocalTestClient

    from src.ui.app import create_app

    monkeypatch.chdir(tmp_path)
    configs = tmp_path / "configs"
    configs.mkdir()
    custom_data = tmp_path / "custom-data"
    custom_data.mkdir()
    input_path = custom_data / "corpus.txt"
    vocab_path = custom_data / "vocab.json"
    input_path.write_text("alpha\nbeta\n", encoding="utf-8")
    vocab_path.write_text(json.dumps(["a", "b", "e", "h", "l", "p", "t"]), encoding="utf-8")
    (configs / "custom.yaml").write_text(
        "system:\n  device: cpu\n"
        f"data:\n  input_file: {input_path.as_posix()}\n  vocab_file: {vocab_path.as_posix()}\n",
        encoding="utf-8",
    )

    with LocalTestClient(create_app()) as local_client:
        response = local_client.get(
            "/api/explorer/dataset-sample",
            params={"config_path": "configs/custom.yaml"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input_file"] == input_path.as_posix()
    assert payload["total_lines"] == 2
    assert payload["sample_lines"] == ["alpha", "beta"]
    assert payload["vocab_size"] == 7


def test_explorer_tokenize_reports_actual_tokenizer_semantics_from_configured_vocab(
    tmp_path, monkeypatch
):
    from fastapi.testclient import TestClient as LocalTestClient

    from src.data.tokenizers import ByteTokenizer
    from src.ui.app import create_app

    monkeypatch.chdir(tmp_path)
    configs = tmp_path / "configs"
    configs.mkdir()
    custom_data = tmp_path / "custom-data"
    custom_data.mkdir()
    vocab_path = custom_data / "byte-vocab.json"
    ByteTokenizer().save_vocab(str(vocab_path))
    (configs / "custom.yaml").write_text(
        f"system:\n  device: cpu\ndata:\n  vocab_file: {vocab_path.as_posix()}\n",
        encoding="utf-8",
    )

    with LocalTestClient(create_app()) as local_client:
        response = local_client.post(
            "/api/explorer/tokenize",
            json={
                "text": "Trăm",
                "tokenizer_type": "char",
                "config_path": "configs/custom.yaml",
            },
        )

    assert response.status_code == 200
    assert response.json()["tokenizer_type"] == "byte"


def test_diagnostics_inspect_returns_effective_model_override_metadata(client: TestClient):
    response = client.get("/api/diagnostics/inspect?n_layer=2&block_size=64")

    assert response.status_code == 200
    payload = response.json()
    assert payload["n_layer"] == 2
    assert payload["block_size"] == 64


def test_explorer_dataset_sample_serializes_paths_with_stable_forward_slashes(
    client: TestClient, monkeypatch
):
    """Explorer wire paths stay platform-neutral even when runtime paths use Windows separators."""
    service = _app_state(client).services.inference._service
    original = service.get_engine_config()
    cfg = original.copy(
        data=original.data.copy(
            input_file=r"C:\data\active-corpus.txt",
            vocab_file=r"C:\data\active-vocab.json",
        )
    )
    try:
        service.apply_engine_config(cfg)
        monkeypatch.setattr("src.data.api.os.path.isfile", lambda _path: False)
        res = client.get("/api/explorer/dataset-sample")
        assert res.status_code == 200
        data = res.json()
        assert data["input_file"] == "C:/data/active-corpus.txt"
        assert data["vocab_file"] == "C:/data/active-vocab.json"
    finally:
        service.apply_engine_config(original)


def test_explorer_dataset_sample_uses_active_engine_config(client: TestClient, tmp_path):
    """Explorer must inspect the same data/vocab paths currently applied to runtime."""
    from src.data.tokenizers import CharTokenizer

    state = _app_state(client)
    service = state.services.inference._service
    original = service.get_engine_config()
    input_file = tmp_path / "active-corpus.txt"
    vocab_file = tmp_path / "active-vocab.json"
    input_file.write_text("alpha\nbeta\n", encoding="utf-8")
    CharTokenizer(text="alphabet\n").save_vocab(str(vocab_file))
    cfg = original.copy(
        data=original.data.copy(input_file=str(input_file), vocab_file=str(vocab_file))
    )
    try:
        service.apply_engine_config(cfg)
        res = client.get("/api/explorer/dataset-sample")
        assert res.status_code == 200
        data = res.json()
        assert data["input_file"] == str(input_file).replace("\\", "/")
        assert data["sample_lines"] == ["alpha", "beta"]
        assert data["vocab_size"] == len(CharTokenizer.load_vocab(str(vocab_file)).chars)
    finally:
        service.apply_engine_config(original)


def test_explorer_char_tokenizer_does_not_reuse_incompatible_loaded_byte_tokenizer(
    client: TestClient, tmp_path
):
    """A request labelled char must actually execute the canonical char tokenizer."""
    from src.data.tokenizers import ByteTokenizer, CharTokenizer

    state = _app_state(client)
    service = state.services.inference._service
    original_config = service.get_engine_config()
    original_tokenizer = service._runtime.tokenizer
    vocab_file = tmp_path / "char-vocab.json"
    CharTokenizer(text="Trăm năm").save_vocab(str(vocab_file))
    cfg = original_config.copy(
        data=original_config.data.copy(vocab_file=str(vocab_file), tokenizer_type="char")
    )
    try:
        service.apply_engine_config(cfg)
        service._runtime.tokenizer = ByteTokenizer()
        res = client.post("/api/explorer/tokenize", json={"text": "Trăm", "tokenizer_type": "char"})
        assert res.status_code == 200
        data = res.json()
        assert data["tokenizer_type"] == "char"
        assert len(data["token_ids"]) <= len("Trăm")
    finally:
        service._runtime.tokenizer = original_tokenizer
        service.apply_engine_config(original_config)


def test_diagnostics_inspect_reports_effective_model_overrides(client: TestClient):
    """Inspector metadata must describe the model that was actually instantiated."""
    res = client.get("/api/diagnostics/inspect?n_layer=2&block_size=64")
    assert res.status_code == 200
    data = res.json()
    assert data["n_layer"] == 2
    assert data["block_size"] == 64


def test_slow_checkpoint_listing_does_not_block_control_plane(client: TestClient, monkeypatch):
    import asyncio
    import time

    import httpx

    service = _app_state(client).services.inference._service

    def slow_list_checkpoints():
        time.sleep(0.20)
        return []

    monkeypatch.setattr(service, "list_checkpoints", slow_list_checkpoints)

    async def exercise():
        transport = httpx.ASGITransport(app=client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            started = time.perf_counter()
            listing = asyncio.create_task(async_client.get("/api/checkpoints"))
            await asyncio.sleep(0.01)
            health = await async_client.get("/healthz")
            health_elapsed = time.perf_counter() - started
            await listing
            return health, health_elapsed

    health, health_elapsed = asyncio.run(exercise())
    assert health.status_code == 200
    assert health_elapsed < 0.12


def test_slow_checkpoint_load_does_not_block_control_plane(client: TestClient, monkeypatch):
    import asyncio
    import time

    import httpx

    service = _app_state(client).services.inference._service

    def slow_load_checkpoint(path, backend=None, **kwargs):
        time.sleep(0.20)

    monkeypatch.setattr(service, "load_checkpoint", slow_load_checkpoint)

    async def exercise():
        transport = httpx.ASGITransport(app=client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            started = time.perf_counter()
            loading = asyncio.create_task(
                async_client.post(
                    "/api/checkpoints/load",
                    json={"path": "fake.pt"},
                )
            )
            await asyncio.sleep(0.01)
            health = await async_client.get("/healthz")
            health_elapsed = time.perf_counter() - started
            response = await loading
            return health, health_elapsed, response

    health, health_elapsed, response = asyncio.run(exercise())
    assert response.status_code == 200
    assert health.status_code == 200
    assert health_elapsed < 0.12


def test_slow_training_start_handoff_does_not_block_control_plane(client: TestClient, monkeypatch):
    import asyncio
    import time

    import httpx

    state = _app_state(client)

    def slow_start_training(*args, **kwargs):
        time.sleep(0.20)

    monkeypatch.setattr(state.services.training._background, "start_training", slow_start_training)

    async def exercise():
        transport = httpx.ASGITransport(app=client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            started = time.perf_counter()
            starting = asyncio.create_task(
                async_client.post(
                    "/api/training/start",
                    json={"config_path": "configs/truyen_kieu.yaml"},
                )
            )
            await asyncio.sleep(0.01)
            health = await async_client.get("/healthz")
            health_elapsed = time.perf_counter() - started
            response = await starting
            return health, health_elapsed, response

    health, health_elapsed, response = asyncio.run(exercise())
    assert response.status_code == 200
    assert health.status_code == 200
    assert health_elapsed < 0.12


def test_slow_inference_state_read_does_not_block_control_plane(client: TestClient, monkeypatch):
    import asyncio
    import time

    import httpx

    service = _app_state(client).services.inference._service
    original = service.get_runtime_state

    def slow_state():
        time.sleep(0.20)
        return original()

    monkeypatch.setattr(service, "get_runtime_state", slow_state)

    async def exercise():
        transport = httpx.ASGITransport(app=client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            started = time.perf_counter()
            reading = asyncio.create_task(async_client.get("/api/inference/state"))
            await asyncio.sleep(0.01)
            health = await async_client.get("/healthz")
            health_elapsed = time.perf_counter() - started
            response = await reading
            return health, health_elapsed, response

    health, health_elapsed, response = asyncio.run(exercise())
    assert response.status_code == 200
    assert health.status_code == 200
    assert health_elapsed < 0.12


def test_slow_generation_admission_does_not_block_control_plane(client: TestClient, monkeypatch):
    import asyncio
    import time

    import httpx

    from src.core.exceptions import GenerationNotReadyError

    service = _app_state(client).services.inference._service

    def slow_begin(*args, **kwargs):
        time.sleep(0.20)
        raise GenerationNotReadyError()

    monkeypatch.setattr(service, "begin_generation", slow_begin)

    async def exercise():
        transport = httpx.ASGITransport(app=client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            started = time.perf_counter()
            generating = asyncio.create_task(
                async_client.post("/api/generate/stream", json={"prompt": "hello"})
            )
            await asyncio.sleep(0.01)
            health = await async_client.get("/healthz")
            health_elapsed = time.perf_counter() - started
            response = await generating
            return health, health_elapsed, response

    health, health_elapsed, response = asyncio.run(exercise())
    assert response.status_code >= 400
    assert health.status_code == 200
    assert health_elapsed < 0.12


def test_checkpoint_load_response_uses_authoritative_service_path(client: TestClient, monkeypatch):
    import os

    service = _app_state(client).services.inference._service
    canonical_path = os.path.abspath(os.path.join(service.checkpoint_dir, "best.pt")).replace(
        "\\", "/"
    )

    def fake_load_checkpoint(path, backend=None, **kwargs):
        service._runtime.current_checkpoint_path = canonical_path
        service._runtime.current_checkpoint_identity = (1, 2, 3, 4)

    monkeypatch.setattr(service, "load_checkpoint", fake_load_checkpoint)

    response = client.post("/api/checkpoints/load", json={"path": "best.pt"})

    assert response.status_code == 200
    assert response.json()["current_checkpoint"] == canonical_path


def test_vram_scenarios_use_requested_canonical_device(client: TestClient, monkeypatch):
    captured = {}

    def fake_analyze_vram_scenarios(**kwargs):
        captured.update(kwargs)
        return {
            "available_vram_gb": 0.0,
            "safety_margin_gb": 0.5,
            "scenarios": [],
            "recommended": None,
        }

    monkeypatch.setattr(
        "src.application.diagnostics.service.analyze_vram_scenarios",
        fake_analyze_vram_scenarios,
    )

    response = client.post("/api/diagnostics/scenarios", json={"device": "cpu"})

    assert response.status_code == 200
    assert captured["system_config"].device == "cpu"


def test_auto_training_run_names_are_collision_resistant():
    from src.application.training import generate_run_name

    first = generate_run_name()
    second = generate_run_name()

    assert first.startswith("kieu_")
    assert second.startswith("kieu_")
    assert first != second
    assert "/" not in first and "\\" not in first
    assert "/" not in second and "\\" not in second


def test_ui_training_start_prepares_inference_residency_before_gpu_training(
    client: TestClient, monkeypatch
):
    training_service = _app_state(client).services.training
    inference_service = _app_state(client).services.inference._service
    calls = []

    from src.core.runtime import ResolvedTrainingPlan

    plan = ResolvedTrainingPlan(
        requested_device="cuda",
        device="cuda",
        device_type="cuda",
        requested_precision="float32",
        precision="float32",
        use_amp=False,
        requested_optimizer="adamw",
        optimizer_type="adamw",
        micro_batch_size=1,
        gradient_accumulation_steps=1,
        effective_batch_size=1,
        gradient_checkpointing=False,
    )
    monkeypatch.setattr(
        "src.application.training.service.resolve_training_plan", lambda config: plan
    )
    monkeypatch.setattr(
        "src.application.training.service.check_memory_feasibility",
        lambda **kwargs: (True, "ok", {"total_estimated_gb": 0.1, "total_estimated_mb": 100}),
    )
    from src.application.inference.contracts import InferenceTrainingHandoff

    def fake_prepare_for_training(device):
        calls.append(("prepare", device))
        return InferenceTrainingHandoff()

    monkeypatch.setattr(
        inference_service,
        "prepare_for_training",
        fake_prepare_for_training,
        raising=False,
    )
    monkeypatch.setattr(
        training_service._background,
        "start_training",
        lambda *args, **kwargs: calls.append(("start", kwargs["plan"].runtime_plan.device)),
    )
    monkeypatch.setattr(inference_service, "apply_engine_config", lambda config: None)

    response = client.post("/api/training/start", json={})

    assert response.status_code == 200
    assert calls[:2] == [("prepare", "cuda"), ("start", "cuda")]


def test_ui_training_start_pins_resume_checkpoint_revision(
    client: TestClient, monkeypatch, tmp_path
):
    import os

    from src.core.runtime import ResolvedTrainingPlan

    training_service = _app_state(client).services.training
    inference_service = _app_state(client).services.inference._service
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    checkpoint = checkpoint_dir / "resume.pt"
    checkpoint.write_bytes(b"pinned-revision")
    stat = os.stat(checkpoint)
    expected = (int(stat.st_dev), int(stat.st_ino), int(stat.st_size), int(stat.st_mtime_ns))
    captured = {}

    plan = ResolvedTrainingPlan(
        requested_device="cpu",
        device="cpu",
        device_type="cpu",
        requested_precision="float32",
        precision="float32",
        use_amp=False,
        requested_optimizer="adamw",
        optimizer_type="adamw",
        micro_batch_size=1,
        gradient_accumulation_steps=1,
        effective_batch_size=1,
        gradient_checkpointing=False,
    )
    monkeypatch.setattr(
        "src.application.training.service.resolve_training_plan", lambda config: plan
    )
    monkeypatch.setattr(
        "src.application.training.service.check_memory_feasibility",
        lambda **kwargs: (True, "ok", {"total_estimated_gb": 0.1, "total_estimated_mb": 100}),
    )
    from src.application.inference.contracts import InferenceTrainingHandoff

    monkeypatch.setattr(
        inference_service,
        "prepare_for_training",
        lambda device: InferenceTrainingHandoff(),
    )
    monkeypatch.setattr(inference_service, "apply_engine_config", lambda config: None)

    def fake_start(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(training_service._background, "start_training", fake_start)

    response = client.post(
        "/api/training/start",
        json={
            "resume_checkpoint": str(checkpoint),
            "overrides": {"training.checkpoint_dir": str(checkpoint_dir)},
        },
    )

    assert response.status_code == 200
    assert captured["plan"].resume_checkpoint_identity == expected


def test_ui_training_start_reports_resume_disappeared_during_revision_pin(
    client: TestClient, monkeypatch, tmp_path
):
    training_service = _app_state(client).services.training
    inference_service = _app_state(client).services.inference._service
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    checkpoint = checkpoint_dir / "resume.pt"
    checkpoint.write_bytes(b"exists-at-validation")

    launch_service = _app_state(client).services.training._launcher
    monkeypatch.setattr(
        launch_service._checkpoint_port,
        "capture_identity",
        lambda path: (_ for _ in ()).throw(FileNotFoundError(path)),
    )

    from src.application.inference.contracts import InferenceTrainingHandoff

    monkeypatch.setattr(
        inference_service,
        "prepare_for_training",
        lambda device: InferenceTrainingHandoff(),
    )
    monkeypatch.setattr(inference_service, "apply_engine_config", lambda config: None)
    monkeypatch.setattr(
        training_service._background, "start_training", lambda *args, **kwargs: None
    )

    response = client.post(
        "/api/training/start",
        json={
            "resume_checkpoint": str(checkpoint),
            "overrides": {"training.checkpoint_dir": str(checkpoint_dir)},
        },
    )

    assert response.status_code == 400
    assert "checkpoint" in response.json()["detail"].lower()
