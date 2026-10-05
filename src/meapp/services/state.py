# Remember the date of MEApp's last successful processing run.
from datetime import date
import json
from pathlib import Path


from meapp.exceptions import errors


class StateService:
    """Manages MEApp's persistent runtime state."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    def get_last_run_date(self) -> date:
        try:
            with self.state_file.open("r", encoding="utf-8") as file:
                state = json.load(file)

            return date.fromisoformat(state["last_run_date"])

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise errors.InvalidStateError(
                f"Invalid state file: {self.state_file}"
            ) from error


    def set_last_run_date(self, date: date) -> None:
        state = {
            "last_run_date": date.isoformat()
        }

        with self.state_file.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=4)
