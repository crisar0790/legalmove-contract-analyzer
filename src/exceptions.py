"""Define application-specific exceptions."""


class LegalMoveError(Exception):
    """Base exception for application errors."""


class ImageValidationError(LegalMoveError):
    """Raised when an input image cannot be safely processed."""
