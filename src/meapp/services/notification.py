"""User-facing progress notices delivered through console and file logs."""

import logging
from datetime import date, datetime


logger = logging.getLogger(__name__)


class NotificationService:
    """Report run status through the configured log handlers."""

    def started(self) -> None:
        self._send(logging.INFO, "MEApp processing started.")

    def retrieving_interval(
        self,
        start: datetime,
        end: datetime,
    ) -> None:
        self._send(
            logging.INFO,
            "Retrieving maintenance messages in [%s, %s).",
            start.isoformat(),
            end.isoformat(),
        )

    def retrieving_date(self, processing_date: date) -> None:
        self._send(
            logging.INFO,
            "Retrieving maintenance messages for %s.",
            processing_date.isoformat(),
        )

    def no_work(self) -> None:
        self._send(
            logging.INFO,
            "No messages are due for processing; the checkpoint was not changed.",
        )

    def completed(
        self,
        start: datetime,
        end: datetime,
        checkpoint_updated: bool,
    ) -> None:
        self._send(
            logging.INFO,
            "MEApp completed for [%s, %s). Automatic checkpoint updated: %s.",
            start.isoformat(),
            end.isoformat(),
            checkpoint_updated,
        )

    def failed(self, message: str) -> None:
        self._send(logging.ERROR, "MEApp failed: %s", message)

    @staticmethod
    def _send(level: int, message: str, *args: object) -> None:
        """A notice must not cause the processing workflow to fail."""
        try:
            logger.log(level, message, *args)
        except Exception:
            # Logging handlers normally contain their own I/O failures.
            pass
