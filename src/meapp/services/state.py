"""Manage the timestamp checkpoint for successful message processing."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from meapp.exceptions import InvalidStateError


logger = logging.getLogger(__name__)
STATE_KEY = "last_successful_cutoff_utc"


class StateService:
    """Read and write MEApp's last successful message cutoff."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def get_last_successful_cutoff(self) -> datetime:
        """Read the checkpoint and return it as a UTC-aware datetime."""
        try:
            with self.state_file.open("r", encoding="utf-8") as file:
                state = json.load(file)

            cutoff = datetime.fromisoformat(state[STATE_KEY])
            if cutoff.tzinfo is None or cutoff.utcoffset() is None:
                raise ValueError("The checkpoint must include a timezone.")

            cutoff_utc = cutoff.astimezone(timezone.utc)
            logger.info("Loaded the last successful message cutoff: %s.", cutoff_utc.isoformat())
            return cutoff_utc
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            logger.error("The timestamp checkpoint is missing or invalid.")
            raise InvalidStateError(
                f"Invalid state file: {self.state_file}"
            ) from error

    def set_last_successful_cutoff(self, cutoff: datetime) -> None:
        """Save a timezone-aware checkpoint in UTC."""
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("The checkpoint must be timezone-aware.")

        cutoff_utc = cutoff.astimezone(timezone.utc)
        state = {STATE_KEY: cutoff_utc.isoformat()}

        try:
            with self.state_file.open("w", encoding="utf-8") as file:
                json.dump(state, file, indent=4)
        except OSError as error:
            logger.error("Could not save the timestamp checkpoint.")
            raise InvalidStateError(
                "Could not save the MEApp state file."
            ) from error

        logger.info(
            "Saved the successful message cutoff: %s.",
            cutoff_utc.isoformat(),
        )
