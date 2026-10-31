"""Tests for image validation and base64 encoding."""

import base64

import pytest
from PIL import Image

from src.exceptions import ImageValidationError
from src.image_parser import encode_contract_image


@pytest.fixture
def image_path(tmp_path):
    """Create a small valid PNG image."""
    path = tmp_path / "contract.png"
    Image.new("RGB", (40, 40), "white").save(path)
    return path


@pytest.mark.parametrize(
    ("image_format", "extension", "expected_mime"),
    [
        ("PNG", "png", "image/png"),
        ("JPEG", "jpg", "image/jpeg"),
    ],
)
def test_encodes_supported_images(tmp_path, image_format, extension, expected_mime):
    path = tmp_path / f"contract.{extension}"
    Image.new("RGB", (40, 40), "white").save(path, format=image_format)

    result = encode_contract_image(path, max_size_bytes=10_000)

    prefix, encoded_content = result.data_uri.split(",", maxsplit=1)
    assert prefix == f"data:{expected_mime};base64"
    assert base64.b64decode(encoded_content) == path.read_bytes()
    assert result.mime_type == expected_mime
    assert result.size_bytes == path.stat().st_size
    assert result.path == path


def test_rejects_missing_file(tmp_path):
    with pytest.raises(ImageValidationError, match="regular file"):
        encode_contract_image(tmp_path / "missing.png", max_size_bytes=10_000)


def test_rejects_directory(tmp_path):
    with pytest.raises(ImageValidationError, match="regular file"):
        encode_contract_image(tmp_path, max_size_bytes=10_000)


def test_rejects_empty_file(tmp_path):
    path = tmp_path / "empty.png"
    path.write_bytes(b"")

    with pytest.raises(ImageValidationError, match="empty"):
        encode_contract_image(path, max_size_bytes=10_000)


def test_rejects_text_disguised_as_image(tmp_path):
    path = tmp_path / "fake.png"
    path.write_text("This is not an image.", encoding="utf-8")

    with pytest.raises(ImageValidationError, match="invalid"):
        encode_contract_image(path, max_size_bytes=10_000)


def test_detects_format_from_content(image_path):
    renamed_path = image_path.with_suffix(".jpg")
    image_path.rename(renamed_path)

    result = encode_contract_image(renamed_path, max_size_bytes=10_000)

    assert result.mime_type == "image/png"
    assert result.data_uri.startswith("data:image/png;base64,")


def test_rejects_unsupported_format(tmp_path):
    path = tmp_path / "contract.gif"
    Image.new("RGB", (40, 40), "white").save(path, format="GIF")

    with pytest.raises(ImageValidationError, match="JPEG and PNG"):
        encode_contract_image(path, max_size_bytes=10_000)


def test_rejects_oversized_image(image_path):
    limit = image_path.stat().st_size - 1

    with pytest.raises(ImageValidationError, match="exceeds"):
        encode_contract_image(image_path, max_size_bytes=limit)


def test_accepts_image_at_exact_size_limit(image_path):
    size = image_path.stat().st_size

    result = encode_contract_image(image_path, max_size_bytes=size)

    assert result.size_bytes == size


def test_rejects_truncated_image(image_path):
    content = image_path.read_bytes()
    image_path.write_bytes(content[: len(content) // 2])

    with pytest.raises(ImageValidationError):
        encode_contract_image(image_path, max_size_bytes=10_000)


def test_reports_read_failure(image_path, monkeypatch):
    def deny_read(*args, **kwargs):
        raise PermissionError("Access denied")

    monkeypatch.setattr(type(image_path), "open", deny_read)

    with pytest.raises(ImageValidationError, match="Unable to read"):
        encode_contract_image(image_path, max_size_bytes=10_000)


@pytest.mark.parametrize("limit", [0, -1])
def test_rejects_invalid_size_limit(image_path, limit):
    with pytest.raises(ValueError, match="positive"):
        encode_contract_image(image_path, max_size_bytes=limit)


def test_accepts_path_with_spaces(image_path):
    renamed_path = image_path.with_name("original contract.png")
    image_path.rename(renamed_path)

    result = encode_contract_image(str(renamed_path), max_size_bytes=10_000)

    assert result.path == renamed_path
