"""Coordinate a complete MEApp processing run."""

import logging
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

from meapp.config.settings import Settings
from meapp.exceptions import InvalidDateRangeError, MEAppError, ZohoMailError
from meapp.excel.writer import ExcelManager
from meapp.locking.instance import InstanceLock
from meapp.parsers.maintenance import maintenance_parser
from meapp.services.notification import NotificationService
from meapp.services.state import StateService
from meapp.zoho.authenticator import ZohoAuthenticator
from meapp.zoho.mail_client import ZohoMailClient
from meapp.config.paths import LOCK_FILE, STATE_FILE, WORKBOOK_FILE


logger = logging.getLogger(__name__)

WORKSHEET_NAME = "MAINTENANCE DATA"


def resolve_date_range(
    start_date: date | None,
    end_date: date | None,
    last_run_date: date,
) -> tuple[date, date]:
    """Resolve omitted boundaries and validate the inclusive date range."""
    resolved_start_date = start_date or last_run_date + timedelta(days=1)
    resolved_end_date = end_date or date.today()

    if resolved_start_date > resolved_end_date:
        raise InvalidDateRangeError(
            "Start date must not be later than the end date."
        )

    return resolved_start_date, resolved_end_date


def generate_processing_dates(
    start_date: date,
    end_date: date,
) -> Iterator[date]:
    """Yield every date in the inclusive range."""
    date_to_process = start_date

    while date_to_process <= end_date:
        yield date_to_process
        date_to_process += timedelta(days=1)


def is_maintenance_mail(mail_subject: object) -> bool:
    """Return whether a subject identifies a new maintenance report email."""
    if not isinstance(mail_subject, str):
        return False

    normalized_subject = mail_subject.strip().lower()
    return (
        normalized_subject.startswith("maintenance report")
        and not normalized_subject.startswith("re:")
    )


def run(
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:
    """Retrieve, parse, and write reports, then record successful completion."""
    notifications = NotificationService()

    try:
        # The lock covers state resolution as well as workbook and Zoho work.
        with InstanceLock(LOCK_FILE):
            notifications.started()
            state_service = StateService(STATE_FILE)
            last_run_date = state_service.get_last_run_date()
            resolved_start_date, resolved_end_date = resolve_date_range(
                start_date,
                end_date,
                last_run_date,
            )

            logger.info(
                "Processing maintenance reports from %s through %s.",
                resolved_start_date.isoformat(),
                resolved_end_date.isoformat(),
            )

            settings = Settings()
            authenticator = ZohoAuthenticator(settings)
            mail_client = ZohoMailClient(authenticator)
            account_id = mail_client.get_account_id()

            with ExcelManager(WORKBOOK_FILE) as excel_manager:
                excel_manager.open_worksheet(WORKSHEET_NAME)

                for processing_date in generate_processing_dates(
                    resolved_start_date,
                    resolved_end_date,
                ):
                    notifications.retrieving_date(processing_date)
                    messages = mail_client.get_messages_for_date(
                        account_id=account_id,
                        processing_date=processing_date,
                    )
                    maintenance_messages = [
                        message
                        for message in messages
                        if is_maintenance_mail(message.get("subject"))
                    ]

                    logger.info(
                        "Found %s maintenance messages for %s.",
                        len(maintenance_messages),
                        processing_date.isoformat(),
                    )

                    for message in maintenance_messages:
                        folder_id = message.get("folderId")
                        message_id = message.get("messageId")
                        if folder_id is None or message_id is None:
                            raise ZohoMailError(
                                "A maintenance message is missing required identifiers."
                            )

                        content = mail_client.get_message_content(
                            account_id=account_id,
                            folder_id=str(folder_id),
                            message_id=str(message_id),
                        )
                        report = maintenance_parser(content, processing_date)
                        excel_manager.write_record(report)

                # Commit workbook writes only after every requested date succeeds.
                excel_manager.save_progress = True

            # Advance state only after workbook save and close succeed.
            state_service.set_last_run_date(resolved_end_date)
            notifications.completed(resolved_end_date)
            return resolved_start_date, resolved_end_date
    except Exception as exc:
        if isinstance(exc, MEAppError):
            failure_message = str(exc)
        else:
            failure_message = f"Unexpected failure ({type(exc).__name__})."
        notifications.failed(failure_message)
        raise
