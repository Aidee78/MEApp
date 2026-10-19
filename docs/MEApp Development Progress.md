# MEApp Development Progress

## Current Phase
Phase 6 in progress: Reliability & Operations.

The repository contains implementation work for Phases 4 and 5, but their
end-to-end behavior has not been re-verified against Zoho and the workbook.
Do not consider those phases or Phase 6 fully verified based on source review
alone.

## Phase 1 Completed

- pyproject.toml
- .gitignore
- .env.example
- .env
- src/meapp/__init__.py
- src/meapp/__main__.py
- src/meapp/cli/__init__.py
- src/meapp/cli/main.py
- src/meapp/config/__init__.py
- src/meapp/config/settings.py
- src/meapp/logging/__init__.py
- src/meapp/logging/setup.py

## Environment

- Python 3.14.7
- Virtual environment: .venv
- Project installed with:
  python -m pip install -e .

## Verified

- python -m meapp works
- meapp command works
- Logging works
- __name__ behavior was tested
- Settings validation is the final Phase 1 test

## Important Design Decisions

- Use logging.getLogger(__name__)
- Logging is configured before application log records are emitted
- Zoho credentials are loaded through .env
- Configuration is centralized in Settings
- MEApp uses a src-based package structure
- MEApp should follow the professional DEApp architecture where appropriate
- No GUI
- No tests/ folder for this practice implementation

## Phase 2

Phase 2: CLI, Dates & State

Planned work:
1. CLI argument handling
2. Date parsing
3. Date validation
4. Date-range logic
5. Persistent state
6. data/state.json
7. Connect CLI to application workflow

## Phase 6: Reliability & Operations — current status

### Timestamp checkpoint update

Implemented in source, pending manual verification:

- Replaced the automatic date checkpoint with `last_successful_cutoff_utc` in UTC.
- Automatic runs search from the saved cutoff through a cutoff captured at run start, so missed scheduled runs can catch up.
- Explicit date options are converted to West Africa Time (UTC+1) calendar-day boundaries. Explicit backfills do not advance the automatic checkpoint.
- The workflow processes one calendar day at a time: search and filter that day's messages, fetch and parse matching content, write rows, then continue to the next day.
- The parser receives each message's local received date as its fallback date.
- Added interval, per-date, message-count, no-work, and checkpoint logs without logging email bodies or credentials.

The existing `data/state.json` must contain a timezone-aware `last_successful_cutoff_utc` value. Old `last_run_date` files are not migrated automatically. Pick the initial timestamp carefully because it determines which messages the next automatic run considers.

Remaining risks include duplicate Excel rows if saving the workbook succeeds but saving the checkpoint fails, and duplicate rows when explicit backfills are repeated. The current source still processes every matching maintenance message and does not select only the latest applicable report.

Implemented during the current work session:

- Added a shared `MEAppError` hierarchy, including configuration, parsing,
  Excel, Zoho, state, date-range, and instance-lock errors.
- Added console and rotating file logging under `logs/meapp.log`.
- Added an OS-managed single-instance lock that is released on process exit.
- Added start, per-date, completion, and failure notices through the configured
  console and file log handlers.
- Connected locking, notifications, and failure propagation to the workflow.
- Kept state advancement after successful workbook save and close.
- Added safe CLI exit status handling and state/Excel diagnostic logging.

Checks completed:

- Python source compilation succeeded.
- `git diff --check` succeeded.
- Manual lock contention, release, and reacquisition check succeeded using a
  temporary lock file.

Checks still pending:

- Parser checks could not run because `dateparser` is not installed in the
  active Python environment.
- Live Zoho and workbook scenarios have not been run. They require explicit
  authorization because they contact Zoho and can modify the user's workbook.
- Failure recovery, log file creation, Excel failure behavior, and state
  non-advancement still need manual verification.
- Retry idempotency remains unresolved: a workbook save followed by a failed
  state update can cause records to be appended again on a later run. Any fix
  must follow the project's documented duplicate-date rule.
- Manually verify date-search boundaries, received-time field names, automatic
  catch-up, explicit backfills, and state non-advancement after failures. Do not
  use the production workbook for these checks; use a copy.

Checks completed for the timestamp change:

- Python AST parsing succeeded for the five changed Python source files.
- `git diff --check` reported no whitespace errors.
- No automated tests, Zoho calls, or workbook operations were run.
