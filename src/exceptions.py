"""Define application-specific exceptions."""


class LegalMoveError(Exception):
    """Base exception for application errors."""


class ImageValidationError(LegalMoveError):
    """Raised when an input image cannot be safely processed."""


class ModelAPIError(LegalMoveError):
    """Raised when a model request fails."""


class ModelResponseError(LegalMoveError):
    """Raised when a model response is empty, refused, or incomplete."""
