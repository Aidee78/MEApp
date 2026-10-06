"""Zoho OAuth Authentication."""

"""
Responsible for authentication only:
* Zoho Oauth credentials
* obtaining an access token
* refreshing an expired token
* caching the token in memory
* reporting authentication failures


eventually it will do this

authenticator = ZohoAuthenticator()
token = authenticator.get_access_token()


Internally:

Read the existing Settings.
Determine the Zoho OAuth token endpoint.
Send the refresh-token request using requests.
Validate the HTTP response.
Extract access_token.
Remember the token in memory.
Remember when it expires.
Return the token.
Refresh it when necessary.
Never expose credentials in logs/errors.

"""

# Authenticator
#     |
#     ├── knows refresh token
#     ├── knows client ID/secret
#     ├── obtains access token
#     ├── caches access token
#     └── refreshes access token


import logging
import time


import requests


from meapp.config.settings import Settings
from meapp.exceptions.errors import ZohoAuthenticationError


logger = logging.getLogger(__name__)


class ZohoAuthenticator:
    """Handles authentication with Zoho"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        self._access_token: str | None = None
        self._access_token_expires_at: float | None = None


    def get_access_token(self) -> str:
        """Return a valid access token."""

        if self._is_access_token_valid():
            logger.info("Using cached Zoho access token.")
            return self._access_token

        if self.settings.zoho_refresh_token:
            logger.info("Refreshing Zoho access token.")
            return self._refresh_access_token()

        logger.info("Obtaining Zoho access token using authorization code.")
        return self._exchange_authorization_code()

    def _exchange_authorization_code(self) -> str:
        """Exchange an authorization code for tokens."""
        
        token_url = (
            f"{self.settings.zoho_accounts_server}/oauth/v2/token"
        )

        params = {
            "code": self.settings.zoho_auth_code,
            "grant_type": "authorization_code",
            "client_id": self.settings.zoho_client_id,
            "client_secret": self.settings.zoho_client_secret,
        }


        try:
            response = requests.post(
                url = token_url,
                data = params,
                timeout = self.settings.timeout,
            )

        except requests.RequestException as exc:
            logger.error(
                "Unable to connect to the Zoho authentication server "
                "during authorization-code exchange."
            )

            raise ZohoAuthenticationError(
                "Unable to connect to the Zoho authentication server."
            ) from exc


        if not response.ok:
            logger.error(
                "Zoho authorization-code exchange failed with HTTP "
                "status %s.",
                response.status_code,
            )

            raise ZohoAuthenticationError(
                f"Zoho authorization-code exchange failed with HTTP "
                f"status {response.status_code}."
            )

        try:
            response_data = response.json()

        except ValueError as exc:
            logger.error(
                "Zoho authorization response contained invalid JSON."
            )

            raise ZohoAuthenticationError(
                "Zoho authorization response returned invalid JSON."
            ) from exc


        access_token = response_data.get("access_token")
        refresh_token = response_data.get("refresh_token")
        expires_in = response_data.get("expires_in")

        
        if not access_token:
            logger.error(
                "Zoho authorization response did not contain an access token."
            )

            raise ZohoAuthenticationError(
                "Zoho authorization response did not contain "
                "an access token."
            )

        if not refresh_token:
            logger.error(
                "Zoho authorization response did not contain a refresh token."
            )

            raise ZohoAuthenticationError(
                "Zoho authorization response did not contain "
                "a refresh token."
            )

        if not isinstance(expires_in, int):
            logger.error(
                "Zoho authorization response contained an invalid "
                "token expiration value."
            )

            raise ZohoAuthenticationError(
                "Zoho authorization response contained an invalid "
                "token expiration value."
            )

        self.settings.save_refresh_token(refresh_token)

        self.settings.zoho_refresh_token = refresh_token

        self._cache_access_token(
            access_token = access_token,
            expires_in = expires_in,
        )

        logger.info(
            "Zoho authorization-code exchange succeeded; "
            "access token cached for %s seconds.",
            expires_in,
        )

        return access_token
    

    def _refresh_access_token(self) -> str:
        """Obtain an access token from Zoho using the refresh token."""

        token_url = f"{self.settings.zoho_accounts_server}/oauth/v2/token"

        params = {
            "refresh_token": self.settings.zoho_refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.settings.zoho_client_id,
            "client_secret": self.settings.zoho_client_secret
        }

        try:
            response = requests.post(
                url = token_url,
                data = params,
                timeout = self.settings.timeout,
            )

        except requests.RequestException as exc:
            logger.error(
                "Unable to connect to the Zoho authentication server "
                "during token refresh."
            )

            raise ZohoAuthenticationError(
                "Unable to connect to the Zoho authentication server."
            ) from exc

        if not response.ok:
            logger.error(
                "Zoho token refresh failed with HTTP status %s.",
                response.status_code,
            )

            raise ZohoAuthenticationError(
                f"Zoho authentication failed with HTTP "
                f"status {response.status_code}"
            )


        try: 
            response_data = response.json()

        except ValueError as e:
            logger.error(
                "Zoho token refresh response contained invalid JSON."
            )

            raise ZohoAuthenticationError(
                "Zoho authentication returned invalid JSON."
            ) from e

        access_token = response_data.get("access_token")
        expires_in = response_data.get("expires_in")

        if not access_token:
            logger.error(
                "Zoho authentication response did not contain "
                "an access token."
            )

            raise ZohoAuthenticationError(
                "Zoho authentication response did not contain an access token."
            )

        if not isinstance(expires_in, int):
            logger.error(
                "Zoho authentication response contained an invalid "
                "token expiration value."
            )

            raise ZohoAuthenticationError(
                "Zoho authentication response contained an "
                "invalid token expiration value."
            )


        self._cache_access_token(
            access_token = access_token,
            expires_in = expires_in,
        )

        logger.info(
            "Zoho access token refreshed successfully; "
            "cached for %s seconds.",
            expires_in,
        )

        return access_token

    def _cache_access_token(
        self, 
        access_token: str, 
        expires_in: int
    ) -> None:
        """Store the access token and its expiration time in memory."""

        self._access_token = access_token
        self._access_token_expires_at = time.time() + expires_in

        logger.info(
            "Zoho access token cached in memory."
        )

    def _is_access_token_valid(self) -> bool:
        """Return whether the cached access token is still valid."""

        if self._access_token is None:
            return False

        if self._access_token_expires_at is None:
            return False

        return time.time() < self._access_token_expires_at

    def invalidate_access_token(self) -> None:
        """Invalidates the cached access token so that the next request must obtain a new one."""
        
        logger.info("Invalidating cached Zoho access token.")

        self._access_token = None
        self._access_token_expires_at = None
