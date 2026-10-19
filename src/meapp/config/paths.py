"""Centralized paths for MEApp resources and runtime files."""

import sys
from pathlib import Path


def get_application_directory() -> Path:
    """Return the directory containing the application installation."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parents[2]

    return Path(__file__).resolve().parents[3]


APP_DIRECTORY = get_application_directory()

ENV_FILE = APP_DIRECTORY / ".env"
RESOURCE_DIRECTORY = APP_DIRECTORY / "resources"
DATA_DIRECTORY = APP_DIRECTORY / "data"
LOG_DIRECTORY = APP_DIRECTORY / "logs"

WORKBOOK_FILE = RESOURCE_DIRECTORY / "maintenance report.xlsx"
STATE_FILE = DATA_DIRECTORY / "state.json"
LOCK_FILE = DATA_DIRECTORY / "meapp.lock"
LOG_FILE = LOG_DIRECTORY / "meapp.log"