import logging
import argparse
from datetime import date


from meapp.logging.setup import setup_logging
from meapp.config import settings
from meapp.application import workflow



def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        # so that the cli can handle the error handling for us
        raise argparse.ArgumentTypeError(
            f"invalid date: {value!r}. Expected format: YYYY-MM-DD"
        )
    

parser = argparse.ArgumentParser(
    prog = "meapp",
    description = "MEApp maintenance reporting application."
) # defines what arguments MEApp accepts.

parser.add_argument(
    "--start-date",
    type = parse_date,
    help = "The date to begin the reporting. Format: YYYY-MM-DD"
)

parser.add_argument(
    "--end-date",
    type = parse_date,
    help = "The date to end the reporting (included). Format: YYYY-MM-DD"
)



def main() -> None:
    cli_args = parser.parse_args() # actually reads what the user supplied

    # First configure the logging infrastructure. Then obtain and use the application logger. 
    
    setup_logging() # Configure logging before the application starts emitting log records that depend on your logging configuration.
    logger = logging.getLogger(__name__)
    
    logger.info("MEApp started.")

    settings.Settings.validate() 


    resolved_start_date, resolved_end_date = workflow.run(
        start_date = cli_args.start_date,
        end_date = cli_args.end_date,
    )

    logger.info(
        "Resolved date range: %s to %s",
        resolved_start_date,
        resolved_end_date
    )
    