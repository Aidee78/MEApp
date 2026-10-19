"""Application configuration.

Responsible for:
* loading configuration from environment variables
* validating required configuration
* providing configuration to other components
* persisting configuration changes when required
"""

import os

from dotenv import find_dotenv,load_dotenv, set_key

from meapp.exceptions import ConfigurationError

from meapp.config.paths import ENV_FILE


# Load the variables from the .env file.
load_dotenv(ENV_FILE)


# configuration names, to avoid repeating myself later
NAME_ZOHO_CLIENT_ID = "ZOHO_CLIENT_ID"
NAME_ZOHO_CLIENT_SECRET = "ZOHO_CLIENT_SECRET"
NAME_ZOHO_REFRESH_TOKEN = "ZOHO_REFRESH_TOKEN"
NAME_ZOHO_ACCOUNTS_SERVER = "ZOHO_ACCOUNTS_SERVER"
NAME_TIMEOUT = "MEAPP_TIMEOUT"
NAME_ZOHO_AUTH_CODE = "ZOHO_AUTH_CODE"



class Settings:
    """Application configuration loaded from environment variables."""

    zoho_auth_code = os.getenv(NAME_ZOHO_AUTH_CODE)
    zoho_client_id = os.getenv(NAME_ZOHO_CLIENT_ID)
    zoho_client_secret = os.getenv(NAME_ZOHO_CLIENT_SECRET)
    zoho_refresh_token = os.getenv(NAME_ZOHO_REFRESH_TOKEN)
    zoho_accounts_server = os.getenv(NAME_ZOHO_ACCOUNTS_SERVER)

    timeout = int(os.getenv(NAME_TIMEOUT, "30"))

    def __init__(self) -> None:
        self.validate()


    @classmethod
    def validate(cls):
        """Validate that all required configuration values are present."""

        required_settings = {
            NAME_ZOHO_CLIENT_ID: cls.zoho_client_id,
            NAME_ZOHO_CLIENT_SECRET: cls.zoho_client_secret,
            NAME_ZOHO_ACCOUNTS_SERVER: cls.zoho_accounts_server,
            NAME_TIMEOUT: cls.timeout
        }

        missing_settings = [
            name
            for name, value in required_settings.items()
            if not value
        ]

        if missing_settings:
            raise ConfigurationError(
                "Missing required environment variables: "
                + ", ".join(missing_settings)
            )

        if not cls.zoho_refresh_token and not cls.zoho_auth_code:
            raise ConfigurationError(
                "Either ZOHO_REFRESH_TOKEN or ZOHO_AUTH_CODE "
                "must be configured."
            )

    def save_refresh_token(self, refresh_token: str) -> None: 
        """Persist the Zoho refresh token to the .env file.""" 
        set_key(
            str(ENV_FILE), 
            NAME_ZOHO_REFRESH_TOKEN, 
            refresh_token, 
        ) 

        self.zoho_refresh_token = refresh_token
