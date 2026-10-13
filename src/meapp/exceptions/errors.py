"""Application-specific exceptions used at component boundaries."""


class MEAppError(Exception):
    """Base class for expected, user-actionable MEApp failures."""


class ConfigurationError(MEAppError):
    """Raised when required application configuration is invalid."""


class InvalidDateRangeError(MEAppError):
    """Raised when the requested processing range is invalid."""


class InvalidStateError(MEAppError):
    """Raised when MEApp's persistent state is missing or invalid."""


class ZohoAuthenticationError(MEAppError):
    """Raised when Zoho authentication fails."""


class ZohoMailError(MEAppError):
    """Raised when communication with the Zoho Mail API fails."""


class ParsingError(MEAppError):
    """Raised when a maintenance email cannot be parsed safely."""


class ExcelWriteError(MEAppError):
    """Raised when the report workbook cannot be updated."""


class InstanceAlreadyRunningError(MEAppError):
    """Raised when another MEApp process holds the application lock."""
