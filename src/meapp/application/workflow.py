"""Coordinate a complete MEApp processing run."""

import logging
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta, timezone

from meapp.config.paths import LOCK_FILE, STATE_FILE, WORKBOOK_FILE
from meapp.config.settings import Settings
from meapp.exceptions import InvalidDateRangeError, MEAppError, ZohoMailError
from meapp.excel.writer import ExcelManager
from meapp.locking.instance import InstanceLock
from meapp.parsers.maintenance import maintenance_parser
from meapp.services.notification import NotificationService
from meapp.services.state import StateService
from meapp.zoho.authenticator import ZohoAuthenticator
from meapp.zoho.mail_client import ZohoMailClient


logger = logging.getLogger(__name__)

WORKSHEET_NAME = "MAINTENANCE DATA"
# Nigeria uses UTC+1 year-round. A fixed offset avoids requiring the optional
# IANA timezone database on Windows installations.
BUSINESS_TIMEZONE = timezone(timedelta(hours=1), name="WAT")


def resolve_time_range(
    start_date: date | None,
    end_date: date | None,
    last_cutoff: datetime,
    run_cutoff: datetime,
) -> tuple[datetime, datetime, bool]:
    """Resolve a half-open received-time interval and explicit-run status."""
    explicit_date_run = start_date is not None or end_date is not None # sets explicit_date_run to False if neither start or end dates were provided, such as in automated runs

    if start_date is None:
        resolved_start = last_cutoff
    else:
        resolved_start = datetime.combine(
            start_date,
            time.min,
            tzinfo=BUSINESS_TIMEZONE,
        )

    if end_date is None:
        resolved_end = run_cutoff
    else:
        # Midnight after the end date is exclusive, covering the full date.
        resolved_end = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=BUSINESS_TIMEZONE,
        )

    if resolved_start.astimezone(timezone.utc) > resolved_end.astimezone(timezone.utc):
        raise InvalidDateRangeError(
            "The start date or timestamp must not be later than the end."
        )

    return resolved_start, resolved_end, explicit_date_run


def is_maintenance_mail(mail_subject: object) -> bool:
    """Return whether a subject identifies a new maintenance report email."""
    if not isinstance(mail_subject, str):
        return False

    normalized_subject = mail_subject.strip().lower()
    return (
        normalized_subject.startswith("maintenance report")
        and not normalized_subject.startswith("re:")
    )


def generate_processing_dates(
    start_date: date,
    end_date: date,
) -> Iterator[date]:
    """Yield every local calendar date in the inclusive range."""
    processing_date = start_date
    while processing_date <= end_date:
        yield processing_date
        processing_date += timedelta(days=1)


def run(
    start_date: date | None,
    end_date: date | None,
) -> tuple[datetime, datetime] | None:
    """Process received messages, then commit the automatic checkpoint."""
    notifications = NotificationService()

    try:
        # The lock covers checkpoint resolution, retrieval, and workbook work.
        with InstanceLock(LOCK_FILE):
            notifications.started()

            # Capture before retrieval. Messages arriving after this point are
            # picked up by the next automatic run.
            run_cutoff = datetime.now(timezone.utc)

            state_service = StateService(STATE_FILE)
            last_cutoff = state_service.get_last_successful_cutoff()

            resolved_start, resolved_end, explicit_date_run = resolve_time_range(
                start_date=start_date,
                end_date=end_date,
                last_cutoff=last_cutoff,
                run_cutoff=run_cutoff,
            )

            start_utc = resolved_start.astimezone(timezone.utc)
            end_utc = resolved_end.astimezone(timezone.utc)

            if start_utc == end_utc:
                notifications.no_work()
                return None

            notifications.retrieving_interval(resolved_start, resolved_end)

            logger.info(
                "Resolved received-time interval [%s, %s).",
                resolved_start.isoformat(),
                resolved_end.isoformat(),
            )

            settings = Settings()
            authenticator = ZohoAuthenticator(settings)
            mail_client = ZohoMailClient(authenticator)
            account_id = mail_client.get_account_id()

            first_day = start_utc.astimezone(BUSINESS_TIMEZONE).date()
            last_day = (
                end_utc - timedelta(microseconds=1)
            ).astimezone(BUSINESS_TIMEZONE).date()

            with ExcelManager(WORKBOOK_FILE) as excel_manager:
                excel_manager.open_worksheet(WORKSHEET_NAME)

                for processing_date in generate_processing_dates(
                    first_day,
                    last_day,
                ):
                    notifications.retrieving_date(processing_date)
                    day_messages = mail_client.get_messages_for_date_between(
                        account_id=account_id,
                        processing_date=processing_date,
                        start=resolved_start,
                        end=resolved_end,
                        local_timezone=BUSINESS_TIMEZONE,
                    )
                    maintenance_messages = [
                        (message, received_at)
                        for message, received_at in day_messages
                        if is_maintenance_mail(message.get("subject"))
                    ]

                    logger.info(
                        "Found %s maintenance messages for %s.",
                        len(maintenance_messages),
                        processing_date.isoformat(),
                    )

                    for message, received_at in maintenance_messages:
                        folder_id = message.get("folderId")
                        message_id = message.get("messageId")
                        if folder_id is None or message_id is None:
                            logger.error(
                                "A maintenance message is missing required identifiers."
                            )
                            raise ZohoMailError(
                                "A maintenance message is missing required identifiers."
                            )

                        content = mail_client.get_message_content(
                            account_id=account_id,
                            folder_id=str(folder_id),
                            message_id=str(message_id),
                        )
                        received_local_date = received_at.astimezone(
                            BUSINESS_TIMEZONE
                        ).date()
                        report = maintenance_parser(content, received_local_date)
                        excel_manager.write_record(report)

                    logger.info(
                        "Finished processing messages received on %s.",
                        processing_date.isoformat(),
                    )

                # The context manager saves/closes before state is advanced.
                excel_manager.save_progress = True

            checkpoint_updated = not explicit_date_run
            if checkpoint_updated:
                state_service.set_last_successful_cutoff(run_cutoff)

            notifications.completed(
                resolved_start,
                resolved_end,
                checkpoint_updated=checkpoint_updated,
            )
            return resolved_start, resolved_end

    except Exception as exc:
        if isinstance(exc, MEAppError):
            failure_message = str(exc)
        else:
            failure_message = f"Unexpected failure ({type(exc).__name__})."
        notifications.failed(failure_message)
        raise
