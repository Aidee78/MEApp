from datetime import date

from meapp.config.settings import Settings
from meapp.zoho.authenticator import ZohoAuthenticator
from meapp.zoho.mail_client import ZohoMailClient


def main() -> None:
    print("=" * 60)
    print("MEApp Phase 3 - Zoho Integration Test")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Load application settings
    # ---------------------------------------------------------
    print("\n[1] Loading settings...")

    settings = Settings()

    print("Settings loaded successfully.")

    # ---------------------------------------------------------
    # 2. Create the authenticator
    # ---------------------------------------------------------
    print("\n[2] Creating Zoho authenticator...")

    authenticator = ZohoAuthenticator(settings)

    print("Authenticator created successfully.")

    # ---------------------------------------------------------
    # 3. Obtain an access token
    # ---------------------------------------------------------
    print("\n[3] Obtaining Zoho access token...")

    access_token = authenticator.get_access_token()

    if not access_token:
        raise RuntimeError("No access token was returned.")

    print("Access token obtained successfully.")
    print("Token value is intentionally not displayed.")

    # ---------------------------------------------------------
    # 4. Verify access-token caching
    # ---------------------------------------------------------
    print("\n[4] Testing access-token cache...")

    cached_token = authenticator.get_access_token()

    if cached_token != access_token:
        raise RuntimeError(
            "Cached access token does not match the original token."
        )

    print("Access-token caching works.")

    # ---------------------------------------------------------
    # 5. Create the Zoho Mail client
    # ---------------------------------------------------------
    print("\n[5] Creating Zoho Mail client...")

    mail_client = ZohoMailClient(authenticator)

    print("Mail client created successfully.")

    # ---------------------------------------------------------
    # 6. Retrieve Zoho Mail account
    # ---------------------------------------------------------
    print("\n[6] Retrieving Zoho Mail account ID...")

    account_id = mail_client.get_account_id()

    if not account_id:
        raise RuntimeError("No Zoho Mail account ID was returned.")

    print(f"Account ID retrieved: {account_id}")

    # ---------------------------------------------------------
    # 7. Retrieve messages for a specific date
    # ---------------------------------------------------------
    #
    # CHANGE THIS DATE to a date on which your Zoho mailbox
    # contains emails.
    #
    processing_date = date(2026, 10, 6)

    print(
        f"\n[7] Retrieving messages for "
        f"{processing_date.isoformat()}..."
    )

    messages = mail_client.get_messages_for_date(
        account_id=account_id,
        processing_date=processing_date,
    )

    print(f"Messages retrieved: {len(messages)}")

    # ---------------------------------------------------------
    # 8. Display safe message metadata
    # ---------------------------------------------------------
    print("\n[8] Inspecting message metadata...")

    if not messages:
        print("No messages were found for this date.")
        print("\nPhase 3 test stopped successfully.")
        return

    first_message = messages[0]

    print("First message metadata:")

    if isinstance(first_message, dict):
        print(f"  messageId: {first_message.get('messageId')}")
        print(f"  folderId:  {first_message.get('folderId')}")
        print(f" Subject: {first_message.get('subject')}")

    else:
        raise RuntimeError(
            "Zoho Mail returned an unexpected message structure."
        )

    # ---------------------------------------------------------
    # 9. Retrieve full content of the first message
    # ---------------------------------------------------------
    print("\n[9] Retrieving full content of first message...")

    message_id = first_message.get("messageId")
    folder_id = first_message.get("folderId")

    if not message_id:
        raise RuntimeError(
            "First message does not contain a messageId."
        )

    if not folder_id:
        raise RuntimeError(
            "First message does not contain a folderId."
        )

    content = mail_client.get_message_content(
        account_id=account_id,
        folder_id=folder_id,
        message_id=message_id,
    )

    if not isinstance(content, str):
        raise RuntimeError(
            "Zoho Mail message content is not a string."
        )

    print("Message content retrieved successfully.")
    print(f"Content length: {len(content)} characters")

    # ---------------------------------------------------------
    # 10. Complete
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("PHASE 3 BASIC TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()