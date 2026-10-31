"""Validate contract images and encode them as data URIs."""

import base64
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from time import perf_counter

from openai import OpenAI
from openai.types.chat import ChatCompletion
from PIL import Image, UnidentifiedImageError

from src.config import Settings, load_settings
from src.exceptions import ImageValidationError, ModelResponseError
from src.llm_client import (
    build_vision_client,
    call_with_retries,
    validate_completion_text,
)

SUPPORTED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
}


@dataclass(frozen=True)
class EncodedImage:
    """Validated image ready for a multimodal request."""

    path: Path
    mime_type: str
    size_bytes: int
    data_uri: str


def _read_image(path: Path, max_size_bytes: int) -> bytes:
    """Read an image while enforcing the configured byte limit."""
    try:
        if not path.is_file():
            raise ImageValidationError(
                f"Image does not exist or is not a regular file: {path}"
            )

        with path.open("rb") as image_file:
            content = image_file.read(max_size_bytes + 1)
    except OSError:
        raise ImageValidationError(f"Unable to read image: {path}") from None

    if not content:
        raise ImageValidationError(f"Image is empty: {path}")
    if len(content) > max_size_bytes:
        raise ImageValidationError(
            f"Image exceeds the {max_size_bytes}-byte limit: {path}"
        )
    return content


def _detect_mime_type(content: bytes) -> str:
    """Inspect actual image content and reject unsupported formats."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(BytesIO(content)) as image:
                mime_type = SUPPORTED_FORMATS.get(image.format)
                if mime_type is None:
                    raise ImageValidationError("Only JPEG and PNG are supported.")
                image.verify()

            with Image.open(BytesIO(content)) as image:
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ImageValidationError(
            "Image content is invalid, corrupted, or unsafe to decode."
        ) from None

    return mime_type


def encode_contract_image(
    path: str | Path,
    *,
    max_size_bytes: int,
) -> EncodedImage:
    """Validate an image and encode its original bytes without modification."""
    if max_size_bytes <= 0:
        raise ValueError("max_size_bytes must be positive.")

    image_path = Path(path)
    content = _read_image(image_path, max_size_bytes)
    mime_type = _detect_mime_type(content)
    encoded_content = base64.b64encode(content).decode("ascii")

    return EncodedImage(
        path=image_path,
        mime_type=mime_type,
        size_bytes=len(content),
        data_uri=f"data:{mime_type};base64,{encoded_content}",
    )


VISION_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "vision.md"


@dataclass(frozen=True)
class ParsedDocument:
    """Transcribed text with measured API usage and execution metadata."""

    text: str
    model: str
    response_id: str
    finish_reason: str
    usage: dict[str, object] | None
    latency_seconds: float


def _request_transcription(
    image: EncodedImage,
    *,
    client: OpenAI,
    settings: Settings,
    prompt: str,
) -> ChatCompletion:
    """Send a validated image to the configured vision model."""
    return client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Transcribe this document image faithfully.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image.data_uri,
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_completion_tokens=settings.vision_max_output_tokens,
    )


def _parse_with_client(
    image: EncodedImage,
    *,
    client: OpenAI,
    settings: Settings,
    prompt: str,
) -> ParsedDocument:
    """Perform transcription and reject unusable responses."""
    started = perf_counter()
    response = call_with_retries(
        lambda: _request_transcription(
            image, client=client, settings=settings, prompt=prompt
        ),
        max_retries=settings.max_retries,
    )
    elapsed = perf_counter() - started

    if not response.choices:
        raise ModelResponseError("The model returned no completion choices.")

    choice = response.choices[0]
    text = validate_completion_text(
        choice.message.content,
        finish_reason=choice.finish_reason,
        refusal=choice.message.refusal,
    )
    return ParsedDocument(
        text=text,
        model=response.model,
        response_id=response.id,
        finish_reason=choice.finish_reason,
        usage=response.usage.model_dump() if response.usage is not None else None,
        latency_seconds=elapsed,
    )


def parse_contract_document(
    path: str | Path,
    *,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> ParsedDocument:
    """Validate and transcribe an image, retaining internal metadata."""
    configuration = settings if settings is not None else load_settings()
    image = encode_contract_image(
        path, max_size_bytes=configuration.max_image_size_bytes
    )
    prompt = VISION_PROMPT_PATH.read_text(encoding="utf-8")

    if client is not None:
        return _parse_with_client(
            image, client=client, settings=configuration, prompt=prompt
        )

    with build_vision_client(configuration) as owned_client:
        return _parse_with_client(
            image, client=owned_client, settings=configuration, prompt=prompt
        )


def parse_contract_image(
    path: str | Path,
    *,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> str:
    """Return only the transcribed text through the public parser interface."""
    return parse_contract_document(path, settings=settings, client=client).text
