from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.exceptions import ConfigurationError, CudaUnavailableError
from src.ui.errors import register_ai_engine_error_handlers


def _client_for(error):
    app = FastAPI()
    register_ai_engine_error_handlers(app)

    @app.get("/fail")
    async def fail():
        raise error

    return TestClient(app)


def test_configuration_error_preserves_structured_core_contract():
    error = ConfigurationError(
        "invalid config",
        details={"field": "model.n_head"},
        suggestion="fix model.n_head",
    )
    with _client_for(error) as client:
        response = client.get("/fail")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_type"] == "ConfigurationError"
    assert payload["error_code"] == "ERR_CFG_INVALID"
    assert payload["message"] == "invalid config"
    assert payload["details"] == {"field": "model.n_head"}
    assert payload["suggestion"] == "fix model.n_head"
    assert payload["is_recoverable"] is False


def test_hardware_error_uses_service_unavailable_without_losing_taxonomy():
    with _client_for(CudaUnavailableError()) as client:
        response = client.get("/fail")

    assert response.status_code == 503
    assert response.json()["error_code"] == "ERR_HW_CUDA_UNAVAILABLE"
