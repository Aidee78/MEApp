"""Application-specific exceptions."""

class InvalidStateError(Exception):
    """Raised when MEApp's persistent state is missing or invalid."""

class ZohoAuthenticationError(Exception):
    """Raised when Zoho Authentication fails."""

class ZohoMailError(Exception):
    """Raised when communication with the Zoho Mail API fails."""