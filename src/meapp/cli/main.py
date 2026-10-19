"""Command-line entry point for MEApp."""

import argparse
import logging
import traceback
from datetime import date

from meapp.application import workflow
from meapp.config import settings
from meapp.exceptions import MEAppError
from meapp.logging.setup import setup_logging


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"invalid date: {value!r}. Expected format: YYYY-MM-DD"
        ) from error


parser = argparse.ArgumentParser(
    prog="meapp",
    description="MEApp maintenance reporting application.",
)
parser.add_argument(
    "--start-date",
    type=parse_date,
    help="Inclusive start calendar date. Format: YYYY-MM-DD",
)
parser.add_argument(
    "--end-date",
    type=parse_date,
    help="Inclusive end calendar date. Format: YYYY-MM-DD",
)


def main() -> int:
    cli_args = parser.parse_args()
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("MEApp started.")
    try:
        settings.Settings.validate()
        result = workflow.run(
            start_date=cli_args.start_date,
            end_date=cli_args.end_date,
        )

        if result is None:
            logger.info("No processing interval was due.")
        else:
            resolved_start, resolved_end = result
            logger.info(
                "Processed received-time interval [%s, %s).",
                resolved_start.isoformat(),
                resolved_end.isoformat(),
            )

        logger.info("MEApp stopped successfully.")
        return 0
    except MEAppError as exc:
        # Application exception messages are designed to contain no secrets.
        logger.error("MEApp stopped with an error: %s", exc)
        logger.info("MEApp stopped.")
        return 1
    except Exception as exc:
        # Do not print arbitrary exception text; third-party errors can contain
        # request data. Components should wrap errors with safe context.
        logger.error(
            "MEApp stopped after an unexpected error (%s).",
            type(exc).__name__,
        )
        for frame in traceback.extract_tb(exc.__traceback__):
            logger.error(
                "Failure location: %s:%s in %s.",
                frame.filename,
                frame.lineno,
                frame.name,
            )
        logger.info("MEApp stopped.")
        return 1
