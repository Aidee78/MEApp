# Remember the date of MEApp's last successful processing run.
from datetime import date
import json
import logging
from pathlib import Path


from meapp.exceptions import errors


logger = logging.getLogger(__name__)


class StateService:
    """Manages MEApp's persistent runtime state."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    def get_last_run_date(self) -> date:
        try:
            with self.state_file.open("r", encoding="utf-8") as file:
                state = json.load(file)

            last_run_date = date.fromisoformat(state["last_run_date"])
            logger.info("Loaded last successful processing date.")
            return last_run_date

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            logger.error("Persistent processing state is invalid.")
            raise errors.InvalidStateError(
                f"Invalid state file: {self.state_file}"
            ) from error
        except OSError as error:
            logger.error("Could not read persistent processing state.")
            raise errors.InvalidStateError(
                "Could not read the MEApp state file."
            ) from error


    def set_last_run_date(self, date: date) -> None:
        state = {
            "last_run_date": date.isoformat()
        }

        try:
            with self.state_file.open("w", encoding="utf-8") as file:
                json.dump(state, file, indent=4)
        except OSError as error:
            logger.error("Could not save persistent processing state.")
            raise errors.InvalidStateError(
                "Could not save the MEApp state file."
            ) from error

        logger.info("Updated last successful processing date to %s.", date.isoformat())
