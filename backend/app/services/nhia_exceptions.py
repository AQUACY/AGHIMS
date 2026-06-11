"""Shared NHIA integration exceptions."""


class NhiaIntegrationError(Exception):
    """Raised when NHIA CCC lookup or generation fails."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable
