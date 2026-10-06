#     MailClient
#       |
#       +-- build Mail API request
#       |
#       +-- obtain token from Authenticator
#       |
#       +-- send HTTP request
#       |
#       +-- handle HTTP response
#       |
#       +-- recover once from 401
#       |
#       +-- return Zoho response/data

from datetime import date
import logging
import time

import requests

from meapp.exceptions.errors import ZohoMailError
from meapp.zoho.authenticator import ZohoAuthenticator


logger = logging.getLogger(__name__)


class ZohoMailClient:
    ZOHO_API_BASE = "https://mail.zoho.com/api"
    REQUEST_TIMEOUT = 30
    MAX_REQUEST_ATTEMPTS = 3
    RETRY_DELAY = 2


    def __init__(
        self,
        authenticator: ZohoAuthenticator,
    ) -> None:
        self.authenticator = authenticator

    def _send_request(
        self,
        method: str,
        url: str,
        headers: dict,
        **kwargs,
    ) -> requests.Response:

        """
        Sends an HTTP request to Zoho Mail.

        Timeout failures are retried up to MAX_REQUEST_ATTEMPTS.
        """

        for attempt in range(1, self.MAX_REQUEST_ATTEMPTS + 1):
            try:
                logger.info(
                    "Sending Zoho Mail request: %s %s "
                    "(attempt %s/%s).",
                    method,
                    url,
                    attempt,
                    self.MAX_REQUEST_ATTEMPTS,
                )
                
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    timeout=self.REQUEST_TIMEOUT,
                    **kwargs,
                )
                
                logger.info(
                    "Zoho Mail returned HTTP status %s for %s %s.",
                    response.status_code,
                    method,
                    url,
                )
                
                return response
            
            except requests.exceptions.Timeout as exc:
                logger.warning(
                    "Zoho Mail request timed out: %s %s "
                    "(attempt %s/%s).",
                    method,
                    url,
                    attempt,
                    self.MAX_REQUEST_ATTEMPTS,
                )

                if attempt == self.MAX_REQUEST_ATTEMPTS:
                    raise ZohoMailError(
                        f"Zoho Mail request timed out after "
                        f"{self.MAX_REQUEST_ATTEMPTS} attempts: "
                        f"{method} {url}"
                    ) from exc

                time.sleep(self.RETRY_DELAY)

            except requests.exceptions.ConnectionError as exc:
                logger.error(
                    "Could not connect to Zoho Mail: %s %s.",
                    method,
                    url,
                )

                raise ZohoMailError(
                    f"Could not connect to Zoho Mail: "
                    f"{method} {url}"
                ) from exc

            except requests.exceptions.RequestException as exc:
                logger.error(
                    "Zoho Mail request failed: %s %s.",
                    method,
                    url,
                )

                raise ZohoMailError(
                    f"Zoho Mail request failed: "
                    f"{method} {url}"
                ) from exc


        logger.error(
            "Zoho Mail request failed unexpectedly %s %s.",
            method,
            url,
        )
        raise ZohoMailError(
            f"Zoho Mail request failed unexpectedly: "
            f"{method} {url}"
        )



    def _request(
            self,
            method: str,
            url: str,
            **kwargs,
    ) -> requests.Response:
        """
        Sends a request to Zoho Mail with authentication
        and controlled 401 recovery.
        """

        access_token = self.authenticator.get_access_token()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Zoho-oauthtoken {access_token}"


        response = self._send_request(
            method,
            url,
            headers=headers,
            **kwargs,
        )


        if response.status_code == 401:
            logger.warning(
                "Zoho Mail returned HTTP 401. "
                "Invalidating the cached access token and retrying once."
            )

            self.authenticator.invalidate_access_token()

            access_token = self.authenticator.get_access_token()
            headers["Authorization"] = f"Zoho-oauthtoken {access_token}" # giving the header the new access_token
            
            response = self._send_request(
                method,
                url,
                headers=headers,
                **kwargs,
            )

        if response.ok:
            return response

        logger.error(
            "Zoho Mail API request failed with HTTP status %s: %s %s.",
            response.status_code,
            method,
            url,
        )

        try:
            response.raise_for_status()

        except requests.exceptions.HTTPError as exc:
            raise ZohoMailError(
                f"Zoho Mail API returned HTTP {response.status_code}: "
                f"{method} {url}"
            ) from exc

        raise ZohoMailError(
            f"Zoho Mail request failed: {method} {url}"
        )

    def _get_json(
        self,
        response: requests.Response,
    ) -> dict:
        """
        Converts a Zoho response into JSON.

        Raises ZohoMailError when the response is not valid JSON.
        """

        try:
            return response.json()

        except ValueError as exc:
            logger.error(
                "Zoho Mail returned an invalid JSON response."
            ) 

            raise ZohoMailError(
                "Zoho Mail returned an invalid JSON response."
            ) from exc

    def get_accounts(self) -> dict:
        """Gets the Zoho mail accounts available to the user."""

        logger.info("Retrieving Zoho Mail accounts.")

        accounts_url = f"{self.ZOHO_API_BASE}/accounts"

        response = self._request(
            "GET",
            accounts_url,
        )

        return self._get_json(response)
    

    def get_account_id(self) -> str:
        """Gets the Zoho Mail account ID."""

        logger.info("Retrieving Zoho Mail account ID.")

        response = self._request(
            "GET",
            f"{self.ZOHO_API_BASE}/accounts",
        )

        data = self._get_json(response)

        if data.get("status", {}).get("code") != 200:
            logger.error(
                "Zoho Mail returned an unsuccessful account response."
            )

            raise ZohoMailError(
                "Zoho Mail returned an unsuccessful account response."
            )
        

        try:
            account_id = data["data"][0]["accountId"]
    
        except (KeyError, IndexError, TypeError) as exc:
            logger.error(
                "Zoho Mail account response did not contain an account ID."
            )
    
            raise ZohoMailError(
                "Zoho Mail account response did not contain an account ID."
            ) from exc
    
        logger.info("Zoho Mail account ID retrieved successfully.")
    
        return account_id
        

    def get_messages(
        self,
        account_id: str,
        params: dict | None = None,
    ) -> dict:
        """Gets messages for a Zoho Mail account."""

        logger.info(
            "Retrieving Zoho Mail messages for account."
        )

        messages_url = (
            f"{self.ZOHO_API_BASE}/accounts/{account_id}/messages"
        )

        response = self._request(
            "GET",
            messages_url,
            params=params,
        )

        return self._get_json(response)
    

    def get_messages_for_date(
        self,
        account_id: str,
        processing_date: date,
        limit_per_page: int = 100,
    ) -> list[dict]:
        """
        Gets ALL messages received on a single specific date, 
        automatically handling API pagination.
        """

        logger.info(
            "Retrieving Zoho Mail messages for %s.",
            processing_date.isoformat(),
        )

        zoho_date_str = processing_date.strftime("%d-%b-%Y")

        search_url = f"{self.ZOHO_API_BASE}/accounts/{account_id}/messages/search"
        search_key = f"fromDate:{zoho_date_str}::toDate:{zoho_date_str}"

        all_messages = []

        start_index = 1  # Zoho API pagination starts at index 1
        has_more_pages = True

        # Clamp the limit between 1 and 200 to meet Zoho's validation constraints
        limit_per_page = max(1, min(limit_per_page, 200))

        while has_more_pages:
            params = {
                "includeto": "true",
                "searchKey": search_key,
                "start": start_index,
                "limit": limit_per_page
            }

            logger.info(
                "Retrieving Zoho Mail page starting at index %s "
                "with limit %s.",
                start_index,
                limit_per_page,
            )

            response = self._request(
                "GET",
                search_url,
                params=params,
            )
            
            response_data = self._get_json(response)
            page_messages = response_data.get("data", [])

            if not isinstance(page_messages, list):
                logger.error(
                    "Zoho Mail returned invalid message data."
                )

                raise ZohoMailError(
                    "Zoho Mail returned invalid message data."
                )

            if page_messages:

                all_messages.extend(page_messages)

                logger.info(
                    "Retrieved %s Zoho Mail messages in current page.",
                    len(page_messages),
                )

                # If we received fewer items than requested, we've hit the last page
                if len(page_messages) < limit_per_page:
                    has_more_pages = False
                else:
                    # Move the cursor forward for the next iteration
                    start_index += limit_per_page
            else:
                # No more data returned
                has_more_pages = False

        logger.info(
            "Retrieved %s Zoho Mail messages for %s.",
            len(all_messages),
            processing_date.isoformat(),
        )

        return all_messages
        # all_messages is a list containing:
        # {
        # "URI": "https://mail.zoho.com/api/accounts/123456789/folders/9000000000905/messages/9000000019029",
        # "hasAttachment": 0,
        # "fromAddress": "rebecca@zylker.com",
        # "folderId": 9000000000905,
        # "messageId": 9000000019029,
        # "sender": "Maria Daniel",
        # "summary": "It is extremely important for us to focus on",
        # "status2": "reply",
        # "sentDateInGMT": 1270171976000,
        # "size": 540,
        # "status": "read",
        # "priority": 3,
        # "threadCount": 0,
        # "flagid": 2,
        # "subject": "Marketing Strategy",
        # "threadId": 1,
        # "receivedtime": 1425388373920
        # }

    def get_message_content(
        self,
        account_id: str, 
        folder_id: str, 
        message_id: str
    ) -> str:
        """Gets the full content of an individual email."""

        logger.info(
            "Retrieving content for Zoho Mail message."
        )

        message_url = (
            f"{self.ZOHO_API_BASE}/accounts/{account_id}"
            f"/folders/{folder_id}"
            f"/messages/{message_id}/content"
        )

        response = self._request(
            "GET",
            message_url,
        )

        # sample response

        # {
        #     "status": {
        #         "code": 200,
        #         "description": "success"
        #     },

        #     "data": {
        #         "messageId": 1709876190693100009,
        #         "content": "<meta content=\"text/html;charset=UTF-8\" /><div><div style=\"font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 10pt\"><div style=\"font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 10pt\"><div><br /></div><div>Hello Rebecca<br /></div><div id=\"x_1757349787\"><p><span class=\"x_1727483614colour\" style=\"color: rgb(42, 42, 42)\">Sent using <a style=\"color: rgb(89, 143, 222)\" target=\"_blank\">Zoho Mail</a></span><br /></p></div><div><br b</div></div></div><br /></div>"

        #     }
        # }

        payload = self._get_json(response)
    
        try:
            content = payload["data"]["content"]
    
        except (KeyError, TypeError) as exc:
            logger.error(
                "Zoho Mail response did not contain message content."
            )
    
            raise ZohoMailError(
                "Zoho Mail response did not contain message content."
            ) from exc
    
        logger.info(
            "Zoho Mail message content retrieved successfully."
        )
    
        return content
