"""User-facing errors and stable CLI exit codes."""

from __future__ import annotations


class CliError(RuntimeError):
    """Base class for expected failures that are safe to print."""

    exit_code = 1
    label = "ERROR"
    possibly_billed = False


class ConfigError(CliError):
    """Configuration could not be resolved safely."""

    exit_code = 2
    label = "CONFIG ERROR"


class GenerationError(CliError):
    """An image request or response failed."""

    exit_code = 3

    def __init__(self, message: str, *, possibly_billed: bool = False) -> None:
        super().__init__(message)
        self.possibly_billed = possibly_billed


class GenerationInterrupted(CliError):
    """A user or operating-system signal interrupted an image request."""

    label = "INTERRUPTED"

    def __init__(
        self,
        signal_name: str,
        *,
        request_submitted: bool,
        exit_code: int = 130,
    ) -> None:
        super().__init__(f"Image generation was interrupted by {signal_name}.")
        self.exit_code = exit_code
        self.signal_name = signal_name
        self.request_submitted = request_submitted
        self.possibly_billed = request_submitted
        self.automatic_retry = False


class UpdateError(CliError):
    """Version discovery, download verification, or self-update failed."""

    exit_code = 5
    label = "UPDATE ERROR"
