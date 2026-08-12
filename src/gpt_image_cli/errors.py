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


class UpdateError(CliError):
    """Version discovery, download verification, or self-update failed."""

    exit_code = 5
    label = "UPDATE ERROR"
