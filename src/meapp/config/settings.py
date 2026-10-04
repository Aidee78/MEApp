import os

from dotenv import load_dotenv

load_dotenv() # not passing in the file path forces load_env() to find the .env by itself


# configuration names, to avoid repeating myself later
NAME_ZOHO_CLIENT_ID = "ZOHO_CLIENT_ID"
NAME_ZOHO_CLIENT_SECRET = "ZOHO_CLIENT_SECRET"
NAME_ZOHO_REFRESH_TOKEN = "ZOHO_REFRESH_TOKEN"


class Settings:
    """Application configuration loaded from environment variables."""

    zoho_client_id = os.getenv(NAME_ZOHO_CLIENT_ID)
    zoho_client_secret = os.getenv(NAME_ZOHO_CLIENT_SECRET)
    zoho_refresh_token = os.getenv(NAME_ZOHO_REFRESH_TOKEN)

    @classmethod
    def validate(cls):
        """Validate that all required configuration values are present."""

        required_settings = {
            NAME_ZOHO_CLIENT_ID: cls.zoho_client_id,
            NAME_ZOHO_CLIENT_SECRET: cls.zoho_client_secret,
            NAME_ZOHO_REFRESH_TOKEN: cls.zoho_refresh_token,
        }

        missing_settings = [
            name
            for name, value in required_settings.items()
            if not value
        ]

        if missing_settings:
            raise ValueError(
                "Missing required environment variables: "
                + ", ".join(missing_settings)
            )