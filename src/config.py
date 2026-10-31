"""Load and validate application configuration."""

import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigurationError(ValueError):
    """Raised when application configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    """Validated settings shared by application components."""

    openai_api_key: str = field(repr=False)
    langfuse_public_key: str = field(repr=False)
    langfuse_secret_key: str = field(repr=False)
    langfuse_host: str
    vision_model: str
    agent_model: str
    request_timeout_seconds: float
    max_retries: int
    vision_max_output_tokens: int
    context_max_output_tokens: int
    extraction_max_output_tokens: int
    max_image_size_bytes: int


def _required(values: dict, name: str) -> str:
    """Read a required nonblank value without exposing its contents."""
    value = values.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{name} is required.")
    return value.strip()


def _integer(values: dict, name: str, default: int, minimum: int) -> int:
    """Read an integer constrained by a minimum value."""
    try:
        value = int(values.get(name, str(default)))
    except (TypeError, ValueError):
        raise ConfigurationError(f"{name} must be an integer.") from None

    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}.")
    return value


def _timeout(values: dict) -> float:
    """Read a finite positive timeout."""
    name = "REQUEST_TIMEOUT_SECONDS"
    try:
        value = float(values.get(name, "60"))
    except (TypeError, ValueError):
        raise ConfigurationError(f"{name} must be a positive number.") from None

    if not math.isfinite(value) or value <= 0:
        raise ConfigurationError(f"{name} must be a finite positive number.")
    return value


def _model(
    values: dict,
    name: str,
    default: str = "gpt-4o",
) -> str:
    """Read a nonblank model name with an explicit default."""
    return _required({name: values.get(name, default)}, name)


def load_settings(env_file: Path | None = None) -> Settings:
    """Load settings, giving process environment variables precedence."""
    path = env_file if env_file is not None else PROJECT_ROOT / ".env"
    values = {**dotenv_values(path, interpolate=False), **os.environ}

    return Settings(
        openai_api_key=_required(values, "OPENAI_API_KEY"),
        langfuse_public_key=_required(values, "LANGFUSE_PUBLIC_KEY"),
        langfuse_secret_key=_required(values, "LANGFUSE_SECRET_KEY"),
        langfuse_host=_required(values, "LANGFUSE_HOST"),
        vision_model=_model(values, "VISION_MODEL"),
        agent_model=_model(values, "AGENT_MODEL", "gpt-6-luna"),
        request_timeout_seconds=_timeout(values),
        max_retries=_integer(values, "MAX_RETRIES", 2, 0),
        vision_max_output_tokens=_integer(values, "VISION_MAX_OUTPUT_TOKENS", 4096, 1),
        context_max_output_tokens=_integer(
            values, "CONTEXT_MAX_OUTPUT_TOKENS", 2048, 1
        ),
        extraction_max_output_tokens=_integer(
            values, "EXTRACTION_MAX_OUTPUT_TOKENS", 2048, 1
        ),
        max_image_size_bytes=_integer(values, "MAX_IMAGE_SIZE_BYTES", 10_000_000, 1),
    )
