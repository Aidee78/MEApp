from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

from meapp.services.state import StateService


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATE_FILE = PROJECT_ROOT / "data" / "state.json"


def resolve_date_range(
    start_date: date | None,
    end_date: date | None,
    last_run_date: date,
) -> tuple[date, date]:

    start_date = start_date or last_run_date + timedelta(days=1)
    # because last run date shows the date the application was last run, not when the new processing should start from
    end_date = end_date or date.today()

    if start_date > end_date:
        raise ValueError(
            "Start date must not be greater than end date"
        )

    return start_date, end_date


def generate_processing_dates(
    start_date: date,
    end_date: date,
) -> Iterator[date]:

    date_to_process = start_date

    while date_to_process <= end_date:
        yield date_to_process

        date_to_process += timedelta(days=1)


def run(
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:

    state_service = StateService(STATE_FILE)
    last_run_date = state_service.get_last_run_date() # get last successful run date

    resolved_start_date, resolved_end_date = resolve_date_range(
        start_date,
        end_date,
        last_run_date,
    ) # determine date boundaries

    dates_to_process = generate_processing_dates(
        resolved_start_date,
        resolved_end_date,
    ) # lazily produce dates



    

    for date_to_process in dates_to_process:
        print(date_to_process)
        # perform application logic flow




    state_service.set_last_run_date(resolved_end_date)

    return resolved_start_date, resolved_end_date


"""
run()
 |
 +-- get last successful run
 |
 +-- resolve dates
 |
 +-- generate dates to process
 |
 +-- for each date:
 |      |
 |      +-- retrieve relevant Zoho mail
 |      +-- parse maintenance information
 |      +-- apply business rules
 |      +-- produce structured data
 |
 +-- write results to Excel
 |
 +-- update last_run_date
 |
 +-- log successful completion
"""