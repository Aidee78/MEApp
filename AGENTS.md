# MEApp instructions for Codex

## Project purpose
MEApp is a learning-oriented practice implementation of DEApp. The goal is to build a maintainable Python application while understanding its architecture and implementation decisions, not merely to generate code.

## Working style
- Make small, incremental changes. Explain the design reason before a significant implementation and explain code changes clearly.
- Inspect the existing code and documentation before proposing or editing files. Treat the current source code and current Git working tree as the implementation baseline.
- Do not recreate the project or perform broad refactors without a concrete reason.
- Preserve completed and verified work in Phases 1–3 unless a specific defect requires a change.
- Give complete code or complete patches when requested, then explain them.
- Prefer explicit type annotations and clear names.
- Do not use the right-arrow symbol in code explanations.
- The user prefers manual verification at this stage and does not want an automated unit-test suite added by default. Do not delete existing manual diagnostic scripts without first confirming they are no longer needed.

## Architecture
- `src/meapp/cli/`: command-line arguments and date input validation.
- `src/meapp/application/`: orchestration and end-to-end workflow.
- `src/meapp/config/`: settings and environment configuration.
- `src/meapp/zoho/`: Zoho OAuth lifecycle and Mail API integration.
- `src/meapp/parsers/`: parse raw maintenance emails.
- `src/meapp/models/`: structured maintenance records.
- `src/meapp/processor/`: business rules and selection/validation of records.
- `src/meapp/excel/`: Excel workbook interaction, using `xlwings` where required.
- `src/meapp/services/`: persistent state and supporting services.
- `src/meapp/locking/`: single-instance protection.
- `src/meapp/logging/`: centralized logging configuration.
- `src/meapp/exceptions/`: application-specific exceptions.
- `resources/`: required workbook resources.
- `data/`: persistent runtime state.

Keep OAuth in `ZohoAuthenticator`; `ZohoMailClient` should call the authenticator rather than implement its own OAuth flow.

## Existing business rules and interfaces to preserve
- CLI date options are `--start-date YYYY-MM-DD` and `--end-date YYYY-MM-DD`; dates are not positional arguments.
- By default, processing starts one day after `last_run_date` and ends today. Explicit dates override their respective defaults. Reject an end date earlier than the start date.
- `data/state.json` stores `last_run_date`, meaning the latest date whose processing completed successfully. Advance it only after the entire requested operation succeeds.
- `generate_processing_dates()` yields every date in the inclusive range.
- For each report date, when multiple maintenance emails compete, the project's specified rule is to retain the most recently sent applicable report. Verify the existing implementation and source specification before changing this rule.
- The email's sent/received date is not necessarily the report date; parse the report date from the email content.
- Do not assume duplicate report dates in Excel are automatically invalid. Inspect the real workbook and the documented business rule before changing existing rows.
- Never log OAuth tokens, client secrets, authorization codes, Authorization headers, email bodies, raw API response bodies, or sensitive email details.

## Secrets and privacy
- Never open, print, copy, or summarize `.env` or any file containing live credentials.
- Do not include `.env`, OAuth tokens, client secrets, authorization codes, real email bodies, or unsanitized email fixtures in generated archives, commits, or prompts.
- Use `.env.example` for configuration names and placeholders.
- Do not make real Zoho API calls or modify a real workbook unless the user explicitly requests that action.
- Avoid destructive edits to Excel files. Work on a copy for workbook experiments unless the user directs otherwise.

## Before making changes
1. Inspect `git status` and the relevant source files.
2. Read `README.md`, `docs/architecture.md`, and `docs/MEApp Development Progress.md`, but verify the progress document against the actual code because it may be stale.
3. Explain any discrepancy between documentation and implementation instead of silently choosing one.
4. Make the smallest coherent change.
5. Run appropriate non-destructive checks. Ask before running any operation that contacts Zoho, writes to the user's workbook, advances persistent state, or otherwise has external side effects.
6. Summarize changed files, rationale, checks performed, and remaining risks.
