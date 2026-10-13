"""User-facing progress notices delivered through console and file logs."""

import logging
from datetime import date


logger = logging.getLogger(__name__)


class NotificationService:
    """Report run status through the configured application log handlers."""

    def started(self) -> None:
        self._send(logging.INFO, "MEApp processing started.")

    def retrieving_date(self, processing_date: date) -> None:
        self._send(
            logging.INFO,
            "Retrieving maintenance reports for %s.",
            processing_date.isoformat(),
        )

    def completed(self, end_date: date) -> None:
        self._send(
            logging.INFO,
            "MEApp completed successfully through %s.",
            end_date.isoformat(),
        )

    def failed(self, message: str) -> None:
        self._send(logging.ERROR, "MEApp failed: %s", message)

    @staticmethod
    def _send(level: int, message: str, *args: object) -> None:
        """A notice must not cause the processing workflow to fail."""
        try:
            logger.log(level, message, *args)
        except Exception:
            # Logging handlers normally contain their own I/O failures. This
            # guard also protects workflow integrity if a custom handler raises.
            pass
