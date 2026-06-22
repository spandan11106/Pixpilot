"""Tests for GET /api/settings and PATCH /api/settings."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.settings import settings
from app.main import app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/settings
# ---------------------------------------------------------------------------


def test_get_settings_returns_masked_keys(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    """A non-empty API key should be returned masked (first4...last4)."""
    monkeypatch.setattr(settings, "openai_api_key", "sk-proj-abcdefghijklmnopwxyz1234")

    response = client.get("/api/settings")
    assert response.status_code == 200

    body = response.json()
    masked = body["openai_api_key"]
    # Must start with first 4 chars and end with last 4 chars of real key
    real = "sk-proj-abcdefghijklmnopwxyz1234"
    assert masked == real[:4] + "..." + real[-4:]
    assert real not in masked  # full key must not appear


def test_get_settings_empty_key_returns_empty_string(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """An unset (empty) API key should be returned as empty string."""
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    response = client.get("/api/settings")
    assert response.status_code == 200

    body = response.json()
    assert body["anthropic_api_key"] == ""


def test_get_settings_short_key_fully_masked(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """A key of 8 chars or fewer must be fully masked as '****'."""
    monkeypatch.setattr(settings, "fal_api_key", "short")

    response = client.get("/api/settings")
    assert response.status_code == 200

    assert response.json()["fal_api_key"] == "****"


def test_get_settings_returns_all_required_keys(client: TestClient):
    """Response must include every required field."""
    required_keys = {
        "openai_api_key",
        "anthropic_api_key",
        "google_api_key",
        "fal_api_key",
        "serpapi_api_key",
        "openai_vision_model",
        "anthropic_vision_model",
        "google_vision_model",
        "summary_model",
        "prompt_model",
        "vision_priority",
    }
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert required_keys <= set(response.json().keys())


def test_get_settings_vision_priority_comma_joined(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """vision_priority must be the comma-joined string from settings.vision_models."""
    monkeypatch.setattr(settings, "vision_models", "google,openai")

    response = client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["vision_priority"] == "google,openai"


# ---------------------------------------------------------------------------
# PATCH /api/settings
# ---------------------------------------------------------------------------


def test_patch_settings_writes_to_dotenv(monkeypatch: pytest.MonkeyPatch, client: TestClient):
    """PATCH should call dotenv.set_key with the correct env var name and value."""
    with patch("app.api.routes.settings.set_key") as mock_set_key:
        response = client.patch(
            "/api/settings",
            json={"openai_api_key": "sk-new-key-abcdefgh"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify set_key was called for OPENAI_API_KEY
    calls = {call.args[1]: call.args[2] for call in mock_set_key.call_args_list}
    assert "OPENAI_API_KEY" in calls
    assert calls["OPENAI_API_KEY"] == "sk-new-key-abcdefgh"


def test_patch_settings_reloads_settings_object(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """After PATCH, a subsequent GET should reflect the new (masked) value."""
    new_key = "sk-updated-key-12345678"

    # Patch set_key to avoid .env writes; also patch Settings() reload to inject value
    with patch("app.api.routes.settings.set_key"), patch(
        "app.api.routes.settings.Settings"
    ) as MockSettings:
        # Configure the fresh Settings instance returned during reload
        fresh_instance = MockSettings.return_value
        fresh_instance.openai_api_key = new_key
        fresh_instance.anthropic_api_key = ""
        fresh_instance.google_api_key = ""
        fresh_instance.fal_api_key = ""
        fresh_instance.serpapi_api_key = ""
        fresh_instance.vision_models = "openai,anthropic,google"
        fresh_instance.openai_vision_model = "gpt-4o"
        fresh_instance.anthropic_vision_model = "claude-3-5-sonnet-20241022"
        fresh_instance.google_vision_model = "gemini-2.0-flash"
        fresh_instance.summary_model = "claude-haiku-4-5-20251001"
        fresh_instance.prompt_model = "claude-sonnet-4-6"
        # Also provide model_fields so the reload loop works
        MockSettings.model_fields = {
            f: None
            for f in [
                "openai_api_key",
                "anthropic_api_key",
                "google_api_key",
                "fal_api_key",
                "serpapi_api_key",
                "vision_models",
                "openai_vision_model",
                "anthropic_vision_model",
                "google_vision_model",
                "summary_model",
                "prompt_model",
                "ffmpeg_sidecar_url",
                "renderer_sidecar_url",
                "content_dir",
                "cors_origins",
            ]
        }
        # Give the fresh instance values for ALL fields so setattr doesn't raise
        fresh_instance.ffmpeg_sidecar_url = settings.ffmpeg_sidecar_url
        fresh_instance.renderer_sidecar_url = settings.renderer_sidecar_url
        fresh_instance.content_dir = settings.content_dir
        fresh_instance.cors_origins = settings.cors_origins

        patch_resp = client.patch("/api/settings", json={"openai_api_key": new_key})
        assert patch_resp.status_code == 200

    # After reload the live settings object should have the new key value
    assert settings.openai_api_key == new_key

    # GET should show the masked form of the new key
    get_resp = client.get("/api/settings")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["openai_api_key"] == new_key[:4] + "..." + new_key[-4:]


def test_patch_settings_vision_priority_writes_vision_models_env(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """vision_priority field must be written to VISION_MODELS env key."""
    with patch("app.api.routes.settings.set_key") as mock_set_key:
        response = client.patch(
            "/api/settings",
            json={"vision_priority": "google,anthropic"},
        )

    assert response.status_code == 200
    calls = {call.args[1]: call.args[2] for call in mock_set_key.call_args_list}
    assert "VISION_MODELS" in calls
    assert calls["VISION_MODELS"] == "google,anthropic"


def test_patch_settings_unknown_field_rejected(client: TestClient):
    """Sending an unknown field should be rejected (extra='forbid')."""
    response = client.patch("/api/settings", json={"unknown_field": "value"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH runtime effects: os.environ and orchestrator reset
# ---------------------------------------------------------------------------


def test_patch_settings_updates_os_environ(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """PATCH must write the new value into os.environ so reloaded Settings picks it up."""
    import os

    new_key = "sk-environ-test-abcdefgh"

    # Register the key with monkeypatch so any writes are reverted after the test.
    monkeypatch.setenv("OPENAI_API_KEY", "__sentinel__")

    with patch("app.api.routes.settings.set_key"):
        client.patch("/api/settings", json={"openai_api_key": new_key})

    assert os.environ.get("OPENAI_API_KEY") == new_key


def test_patch_settings_resets_orchestrator_singleton(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """PATCH must clear the cached VisionOrchestrator so the next get_orchestrator()
    constructs a fresh instance from the updated settings."""
    import app.pipeline.agents.vision_orchestrator as vo_module

    # Isolate the in-place settings mutation so it doesn't leak into later tests.
    # monkeypatch.setattr restores the original value at teardown.
    monkeypatch.setattr(settings, "openai_vision_model", settings.openai_vision_model)
    # Also prevent os.environ leakage from the patch_settings write.
    monkeypatch.setenv("OPENAI_VISION_MODEL", settings.openai_vision_model)

    # Prime the singleton so it is non-None before the PATCH
    _ = vo_module.get_orchestrator()
    assert vo_module._orchestrator is not None

    with patch("app.api.routes.settings.set_key"):
        response = client.patch("/api/settings", json={"openai_vision_model": "gpt-4o-mini"})

    assert response.status_code == 200
    # After PATCH the singleton must have been cleared
    assert vo_module._orchestrator is None

    # get_orchestrator() should rebuild it on next call
    rebuilt = vo_module.get_orchestrator()
    assert rebuilt is not None
    assert vo_module._orchestrator is rebuilt
