# MEApp Architecture

## 1. Purpose and current status

MEApp retrieves maintenance-report emails from Zoho Mail, parses their content into structured records, and writes those records to an Excel workbook. The repository uses a `src`-based Python package and separates CLI handling, configuration, orchestration, external integrations, parsing, persistence, and operational support.

Phase 6 (Reliability & Operations) is still in verification. Phase 7 documentation is underway. The source has not yet been validated end-to-end against live Zoho Mail and the production workbook, so this document describes the **current implementation**, not a claim that all paths are production-ready.

## 2. Component map

| Component | Responsibility in the current source |
|---|---|
| `cli/main.py` | Parses `--start-date` and `--end-date`, configures logging, invokes the workflow, and returns a process exit status. |
| `config/settings.py` | Loads `.env` values, validates required settings, and persists a refresh token after an authorization-code exchange. |
| `application/workflow.py` | Coordinates locking, timestamp-interval resolution, Zoho retrieval, parsing, Excel writes, state advancement, and run notices. |
| `zoho/authenticator.py` | Exchanges an authorization code or refreshes a token, caches the access token in memory, and invalidates it after a 401 response. |
| `zoho/mail_client.py` | Sends authenticated Zoho Mail API requests, retries timeout failures, retries once after HTTP 401, paginates date-based message searches, filters one day's results to a received-time interval, and retrieves message content. |
| `parsers/maintenance.py` | Parses HTML email content into a `MaintenanceReport`, extracting report date, shift, switchovers, generator rating, running time, load, and diesel volume. |
| `models/maintenance.py` | Defines the dataclass used to represent the parsed values. Each field is stored as `(value, flag)`. |
| `processor/maintenance.py` | Currently empty. No business-rule selection/aggregation is implemented in this module. |
| `excel/writer.py` | Opens the workbook with `xlwings`, locates `MAINTENANCE DATA`/`Table2`, appends or reuses a blank final table row, writes columns A–H, applies flag formatting, and saves/closes according to the workflow's success signal. |
| `services/state.py` | Reads and writes the UTC timestamp checkpoint in `data/state.json` and wraps invalid/unreadable state in `InvalidStateError`. |
| `services/notification.py` | Emits start, interval, per-date, no-work, completion, and failure notices through Python logging. |
| `logging/setup.py` | Configures an error-level console handler and an info-level rotating file handler. |
| `locking/instance.py` | Uses an OS-managed file lock to prevent concurrent MEApp runs. |
| `exceptions/errors.py` | Defines the application exception hierarchy. |

## 3. Runtime sequence

1. The CLI parses arguments. Invalid date strings are rejected by `argparse`.
2. Logging is configured before normal application log records are emitted.
3. Configuration is validated.
4. `workflow.run()` acquires `data/meapp.lock`. The operating system releases the lock when its handle is closed or the process exits.
5. The workflow reads `data/state.json` and resolves a half-open received-time interval. Automatic runs use the saved UTC cutoff through a cutoff captured at run start. Explicit date ranges use West Africa Time (UTC+1) midnight boundaries.
6. It creates the Zoho authenticator and mail client, then retrieves the Zoho account ID.
7. It opens `resources/maintenance report.xlsx` and the `MAINTENANCE DATA` worksheet.
8. For each local calendar date touched by the interval, it searches that day's messages, filters them by received timestamp and subject, retrieves each matching body, parses it using the message's received date as the parser fallback, and writes the report before moving to the next date.
9. After every date in the interval is processed, the workflow marks the Excel session for saving. The context manager saves and closes the workbook.
10. Only after workbook save/close succeeds does an automatic run update `last_successful_cutoff_utc`. Explicit-date runs do not advance the automatic checkpoint.
11. Completion is logged. If an exception escapes the workflow, a failure notice is logged and the exception is re-raised for CLI handling.

## 4. Configuration and OAuth

Settings are read from environment variables loaded from `.env`. Required values are `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, and `ZOHO_ACCOUNTS_SERVER`. At least one of `ZOHO_REFRESH_TOKEN` or `ZOHO_AUTH_CODE` must be present. `MEAPP_TIMEOUT` defaults to 30 seconds.

The authenticator first uses a valid in-memory access token. Otherwise, it refreshes through the configured refresh token when one exists, or exchanges the authorization code. The refresh token obtained from the initial authorization exchange is saved through `Settings.save_refresh_token()`. The access token is held only in memory and is not intended to be persisted.

The mail client adds the access token to the authorization header. If a request returns HTTP 401, it invalidates the cached token, obtains a token again, and retries that request once. Timeout failures in the Mail API request path are retried up to three attempts; token endpoint timeout/connection failures are also retried up to three attempts.

Never log credentials, authorization headers, authorization codes, refresh/access tokens, email bodies, or raw API response bodies.

## 5. Date resolution and state

`resolve_time_range()` returns a half-open interval `[start, end)`:

- Automatic run start: `last_successful_cutoff_utc` from state.
- Automatic run end: UTC cutoff captured before retrieval starts.
- Explicit `--start-date`: midnight at the start of that date in West Africa Time (UTC+1).
- Explicit `--end-date`: midnight after that date in West Africa Time, used as an exclusive endpoint.
- An omitted explicit boundary uses the automatic checkpoint or current run cutoff, respectively.
- Explicit-date runs do not advance the automatic checkpoint.
- A start later than the end raises `InvalidDateRangeError`; equal boundaries produce a no-work result.

The workflow processes one local calendar date at a time. For each date, the Zoho client retrieves and paginates that day's candidate messages, then filters them using the received timestamp returned by Zoho. It returns only that day's interval matches; the workflow filters their subjects, fetches their full content, parses them, and writes them before requesting the next date. The received timestamp is compared as an absolute UTC time. The parser gets the message's local received date as its fallback; a report date parsed from the email body may differ.

`StateService` reads `last_successful_cutoff_utc` as an ISO-8601 timezone-aware timestamp and normalizes it to UTC. Missing, malformed, unreadable, or old-format state raises `InvalidStateError`. State is advanced only after the workbook context exits successfully and only for automatic runs.

There is a remaining failure window: the workbook can be saved successfully and the subsequent state write can fail. A later retry can append the same records again. The current implementation does not provide a transaction spanning Excel and the JSON state file, and idempotent recovery has not been implemented. Explicit backfills can also append duplicates when repeated.

## 6. Parsing and business rules

`maintenance_parser()` converts HTML email content to text and extracts the report date/shift and operating values. It returns a `MaintenanceReport`; each field is a `(value, flag)` pair. The Excel writer uses flags to format cells:
- `0`: value found and accepted.
- `1`: fallback/default value used or value not found.
- `2`: value found using an assumed unit.

The report date is extracted from a table row containing “date” where possible. The parser can fall back to a date in text outside tables, then to the processing/mail date. The parser's output date may therefore differ from the date used to search the mailbox.

The workflow currently filters subjects beginning with `maintenance report` and excludes subjects beginning with `re:`. It then writes every matching message's parsed report. The separate `processor/maintenance.py` file is empty, so there is no implemented deduplication or selection of the most recently sent applicable report for a report date in the current workflow. Multiple emails may produce multiple appended rows. The intended duplicate/superseded-message rule must be implemented and manually verified before production use.

## 7. Excel integration

The configured workbook is `resources/maintenance report.xlsx`, worksheet `MAINTENANCE DATA`, table `Table2`. In the supplied snapshot, its table spans columns A–H:
A. REPORT DATE
B. SWITCH OVERS (n)
C. GENERATOR
D. RUNNING TIME (Hour)
E. RUNNING TIME (min)
F. LOAD (KW/Hr)
G. VOL. DIESEL (L)
H. SHIFT

`ExcelManager` uses `xlwings`, so desktop Excel and an appropriate interactive Windows session are normally required. The writer opens the workbook, writes values and flag formatting, and saves only when the workflow sets `save_progress = True` and exits the context without an exception.

The writer's constructor also checks for the same workbook already open in an Excel process, then saves/closes that workbook before opening it for this run. This behavior can affect a workbook a user had open; avoid starting MEApp while manually editing the workbook. Verify the intended workbook-open policy before deployment.

The other workbooks in `resources/` have different table widths (some end at column G). The active workflow points specifically to `maintenance report.xlsx`; do not switch the configured file without checking its headers and columns against `ExcelManager.COLUMNS`.

## 8. Logging, notifications, exceptions, and locking

Logging is configured by `setup_logging()`:
- Console handler: `ERROR` and above.
- File handler: `INFO` and above at `logs/meapp.log`.
- Rotation: 2,000,000 bytes per file, with five backups.
- Log format includes timestamp, level, logger name, and message.

`NotificationService` writes start, per-date retrieval, completion, and failure notices through the configured handlers. These are log-based notices, not email or desktop notifications.

Expected failures derive from `MEAppError`, including configuration, date range, state, Zoho authentication/API, parsing, Excel, and already-running errors. The CLI returns status 1 for handled application failures and unexpected exceptions; success returns 0.

`InstanceLock` uses `msvcrt` on Windows and `fcntl.flock` on POSIX. The lock file may remain on disk after a run; ownership is determined by the OS lock, not by the mere existence of the file.

## 9. Operational risks and verification still required

The following are known from the current source or development status and must not be treated as solved by documentation:

1. **No end-to-end verification yet:** live Zoho and production workbook scenarios have not been run in this review. Verify Zoho's received-time key casing and how its date search includes boundary dates using representative messages.
2. **Retry idempotency:** workbook save followed by state-update failure can lead to duplicate appended records on retry.
3. **Report selection:** the processor module is empty and the workflow writes every filtered message; superseded reports are not selected by the processor.
4. **Failure-path verification:** test that failures during retrieval, parsing, writing, saving, and state update produce the expected exit status and do not advance state prematurely.
5. **Excel lifecycle:** verify workbook-open, save, close, and failure behavior on the intended Windows machine with a backup copy.
6. **Configuration template:** keep `.env.example` synchronized with all required and optional variable names.
7. **Deployment:** executable packaging and Windows Task Scheduler behavior have not been established as verified in this snapshot.

Recommended order: finish Phase 6 manual verification and address critical state/retry behavior; implement and verify the missing report-selection rule; then complete executable packaging, deployment instructions, and Task Scheduler validation.
