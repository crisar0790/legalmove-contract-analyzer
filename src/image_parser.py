"""Validate contract images and encode them as data URIs."""

import base64
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from src.exceptions import ImageValidationError

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
