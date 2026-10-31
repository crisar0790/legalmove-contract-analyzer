"""Tests for configuration loading and validation."""

import os
from dataclasses import fields

import pytest

from src.config import ConfigurationError, Settings, load_settings

REQUIRED_VALUES = {
    "OPENAI_API_KEY": "test-openai-key",
    "LANGFUSE_PUBLIC_KEY": "test-public-key",
    "LANGFUSE_SECRET_KEY": "test-secret-key",
    "LANGFUSE_HOST": "https://langfuse.example.test",
}


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    """Isolate tests from real credentials and local configuration."""
    for setting in fields(Settings):
        monkeypatch.delenv(setting.name.upper(), raising=False)

    path = tmp_path / ".env"
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in REQUIRED_VALUES.items()),
        encoding="utf-8",
    )
    return path


def test_loads_valid_configuration(env_file):
    settings = load_settings(env_file)

    assert settings.openai_api_key == "test-openai-key"
    assert settings.vision_model == "gpt-4o"
    assert settings.agent_model == "gpt-6-luna"
    assert settings.request_timeout_seconds == 60
    assert settings.max_retries == 2


def test_environment_overrides_dotenv(env_file, monkeypatch):
    monkeypatch.setenv("VISION_MODEL", "test-model")

    assert load_settings(env_file).vision_model == "test-model"


@pytest.mark.parametrize("name", REQUIRED_VALUES)
@pytest.mark.parametrize("value", ["", "   "])
def test_rejects_blank_required_values(env_file, monkeypatch, name, value):
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigurationError, match=name):
        load_settings(env_file)


@pytest.mark.parametrize("name", REQUIRED_VALUES)
def test_rejects_missing_required_values(env_file, name):
    env_file.write_text(
        "\n".join(
            f"{key}={value}" for key, value in REQUIRED_VALUES.items() if key != name
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match=name):
        load_settings(env_file)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("REQUEST_TIMEOUT_SECONDS", "0"),
        ("REQUEST_TIMEOUT_SECONDS", "-1"),
        ("REQUEST_TIMEOUT_SECONDS", "invalid"),
        ("REQUEST_TIMEOUT_SECONDS", "nan"),
        ("REQUEST_TIMEOUT_SECONDS", "inf"),
        ("MAX_RETRIES", "-1"),
        ("MAX_RETRIES", "1.5"),
        ("VISION_MAX_OUTPUT_TOKENS", "0"),
        ("CONTEXT_MAX_OUTPUT_TOKENS", "-1"),
        ("EXTRACTION_MAX_OUTPUT_TOKENS", "invalid"),
        ("MAX_IMAGE_SIZE_BYTES", "0"),
        ("VISION_MODEL", " "),
        ("AGENT_MODEL", ""),
    ],
)
def test_rejects_invalid_settings(env_file, monkeypatch, name, value):
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigurationError, match=name):
        load_settings(env_file)


def test_accepts_zero_retries(env_file, monkeypatch):
    monkeypatch.setenv("MAX_RETRIES", "0")

    assert load_settings(env_file).max_retries == 0


def test_secrets_are_excluded_from_representation(env_file):
    representation = repr(load_settings(env_file))

    for name in (
        "OPENAI_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
    ):
        assert REQUIRED_VALUES[name] not in representation


def test_loading_does_not_modify_process_environment(env_file):
    before = dict(os.environ)

    load_settings(env_file)

    assert dict(os.environ) == before
