# MEApp — Maintenance Email Application

MEApp retrieves maintenance-report emails from Zoho Mail, extracts report values, and records them in an Excel workbook. It is a learning-oriented implementation of the DEApp architecture, organized into configuration, CLI, application workflow, Zoho integration, parsing, Excel writing, state, logging, and operational support modules.

> **Implementation status:** Reliability and Operations (Phase 6) is still being verified. Phase 7 documentation has started, but the end-to-end workflow has not yet been verified against live Zoho Mail and the production workbook. Read the known limitations below before running it against real data.

## Requirements

- Windows is the intended deployment environment.
- Python 3.14 or newer, as declared in `pyproject.toml`.
- Microsoft Excel desktop installed and available to the Windows account running MEApp. Excel access is implemented with `xlwings`.
- A Zoho Mail account and OAuth credentials with permission to read the relevant mailbox.
- The maintenance workbook at `resources/maintenance report.xlsx`.

The project currently uses these Python dependencies: `python-dotenv`, `requests`, `xlwings`, `beautifulsoup4`, `lxml`, `word2number`, `dateparser`, and `rapidfuzz`.

## Project layout

```text
MEApp/
├── .env.example                 # Configuration template; no live secrets
├── data/
│   ├── state.json               # Last successfully processed date
│   └── meapp.lock               # Runtime lock file
├── docs/
│   ├── architecture.md          # Component and workflow design
│   └── MEApp Development Progress.md
├── logs/
│   └── meapp.log                # Rotating application log
├── resources/
│   └── maintenance report.xlsx  # Workbook used by the workflow
├── src/meapp/
│   ├── application/workflow.py  # Workflow orchestration
│   ├── cli/main.py              # CLI and process exit status
│   ├── config/settings.py       # Environment configuration
│   ├── exceptions/              # Application exception types
│   ├── excel/writer.py          # Excel workbook operations
│   ├── locking/instance.py      # Single-instance lock
│   ├── logging/setup.py         # Console and rotating file logging
│   ├── models/maintenance.py    # Maintenance report model
│   ├── parsers/maintenance.py   # Email content parser
│   ├── processor/maintenance.py # Reserved for business-rule processing
│   ├── services/                # State and progress notices
│   └── zoho/                    # OAuth and Zoho Mail API
├── pyproject.toml
└── README.md
```

## Installation

Open PowerShell in the project directory.

1. Check the Python version:

   ```powershell
   python --version
   ```

   It should satisfy the project's declared requirement, Python 3.14 or newer.

2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install MEApp and its dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```

The editable installation provides the `meapp` command and also supports `python -m meapp`.

## Configuration

1. Copy `.env.example` to `.env`.
2. Fill in the required Zoho OAuth settings locally.
3. Do not commit or share `.env`; it contains credentials.

Configuration variables:

| Variable | Required | Purpose |
|---|---|---|
| `ZOHO_CLIENT_ID` | Yes | OAuth client ID |
| `ZOHO_CLIENT_SECRET` | Yes | OAuth client secret |
| `ZOHO_ACCOUNTS_SERVER` | Yes | Zoho Accounts base URL for the account's data centre |
| `ZOHO_REFRESH_TOKEN` | One of these is required | Persistent OAuth refresh token |
| `ZOHO_AUTH_CODE` | One of these is required | Short-lived authorization code for initial token exchange |
| `MEAPP_TIMEOUT` | No | HTTP timeout in seconds; defaults to `30` |

Use the Zoho Accounts domain appropriate for the account's data centre. Do not assume every Zoho account uses the same regional domain.

When only an authorization code is configured, MEApp exchanges it for tokens and saves the returned refresh token to `.env`. Authorization codes are short-lived and generally intended for initial authorization, not recurring scheduled runs. After a refresh token is available, keep `ZOHO_REFRESH_TOKEN` configured and remove any expired authorization code.

## Running MEApp

Show the CLI options:

```powershell
meapp --help
```

Or:

```powershell
python -m meapp --help
```

The supported date options are:

```powershell
meapp --start-date 2026-10-01 --end-date 2026-10-05
meapp --start-date 2026-10-01
meapp --end-date 2026-10-05
meapp
```

Dates must use `YYYY-MM-DD`. The end date is inclusive. MEApp rejects a range where the start date is later than the end date.

### Date defaults and state

`data/state.json` contains `last_run_date`, the most recent end date recorded after a successful run.

- If `--start-date` is omitted, the start date is one day after `last_run_date`.
- If `--end-date` is omitted, the end date is the current local system date.
- An explicitly supplied boundary overrides that boundary's default.
- The workflow updates state only after the workbook has been saved and closed successfully.

The state value present in a project snapshot is runtime data, not a recommended value for a new installation. Back up and initialize `data/state.json` deliberately before the first production run. The current implementation raises an application error if the state file is missing or invalid; it does not automatically initialize a missing state file.

**Important:** a workbook save can succeed and the subsequent state-file update can fail. In that case, a retry may append records again. Retry idempotency is a known unresolved operational risk; back up the workbook and do not assume rerunning a failed range is safe until this behavior is addressed.

## What the current workflow does

For each date in the resolved inclusive range, MEApp:

1. Acquires a single-instance operating-system lock.
2. Loads state and resolves the date range.
3. Authenticates with Zoho and retrieves the account ID.
4. Opens `resources/maintenance report.xlsx` and its `MAINTENANCE DATA` worksheet.
5. Retrieves messages for each processing date, filters subjects beginning with `maintenance report` while excluding `re:` replies, and retrieves each matching message's content.
6. Parses report values and writes them into the Excel table.
7. Saves and closes the workbook after all requested dates complete.
8. Advances `last_run_date` and logs successful completion.

The workbook currently configured by the workflow has a `MAINTENANCE DATA` worksheet and a `Table2` table with columns A–H: report date, switch overs, generator, running time in hours, running time in minutes, load, diesel volume, and shift.

The mail search date and the report date parsed from the email body are not necessarily the same. The parser can mark fallback or assumed values in the workbook. Review flagged cells before relying on extracted values.

## Logging and errors

- The console handler displays error-level messages.
- `logs/meapp.log` records information and higher-severity messages.
- The log rotates at approximately 2 MB and retains five backup files.
- Expected application failures use `MEAppError` subclasses and cause a non-zero process exit status.
- The application is designed not to log OAuth secrets or raw email bodies.

Check the log for the operation and safe failure context. Do not add tokens, client secrets, authorization codes, message bodies, or raw API response bodies to logs or support requests.

## Manual diagnostic scripts

The repository contains `test_phase3.py`, `test_parsing_4.py`, and `test_excel_5.py`. These are manual diagnostic scripts, not an automated unit-test suite. Some scripts contact Zoho; `test_excel_5.py` writes to a workbook path hard-coded for a previous machine.

Inspect and adapt a diagnostic script before running it. Do not run it against live services or the production workbook unless that action is intended and the data is backed up.

## Deployment readiness and known limitations

The project is **not yet declared production-ready**. Before unattended deployment:

- Complete manual verification of Phase 6 failure paths, lock behavior, logging, notifications, and state handling.
- Resolve the risk of duplicate appends when workbook save succeeds but state update fails.
- Confirm the intended rule for multiple emails that map to the same report date. The current workflow writes each matching email directly; `src/meapp/processor/maintenance.py` is empty, so a “keep the latest applicable report” rule is not currently enforced there.
- Verify workbook/table compatibility and extraction accuracy against a safe workbook copy and representative, sanitized messages.
- Confirm recovery behavior for missing/invalid state, Zoho authentication failures, API failures, Excel failures, and partial runs.
- Only then build and validate an executable, configure Windows Task Scheduler, and test an unattended run under the intended Windows account.

See [`docs/architecture.md`](docs/architecture.md) for the current component design and workflow details.
