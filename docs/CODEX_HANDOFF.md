# MEApp Codex handoff

## Objective
Continue development of the existing MEApp repository in Codex. This is a continuation, not a rewrite. Read `AGENTS.md` first.

## Current baseline
The latest supplied snapshot is `MEApp 5.zip`, with Git HEAD `3dbed94` (`PHASE 4`, dated 2026-10-08) and a substantial set of working-tree modifications. Do not reset, discard, or overwrite these changes. Inspect `git status` before editing.

Phases 1–3 are described as complete in the prior project checkpoint:
- Phase 1: Python package, settings/environment configuration, logging, CLI entry points.
- Phase 2: CLI date handling and persistent processing state. The current implementation uses a UTC `last_successful_cutoff_utc` timestamp; explicit dates are local calendar-day backfills.
- Phase 3: Zoho OAuth token lifecycle, refresh-token persistence through settings, Zoho Mail API client, pagination, message retrieval, and controlled one-time recovery from HTTP 401.

The current source tree also contains Phase 4/5 work:
- `src/meapp/models/maintenance.py`
- `src/meapp/parsers/maintenance.py`
- `src/meapp/processor/maintenance.py`
- `src/meapp/excel/writer.py`
- `src/meapp/application/workflow.py`
- manual scripts `test_parsing_4.py`, `test_excel_5.py`, and `test_phase3.py`

## Important status discrepancy
`docs/MEApp Development Progress.md` in the supplied snapshot still says Phase 1 is complete and Phase 2 is next. That status is stale compared with the source tree and the later project checkpoints. Update the progress document only after inspecting the implementation and confirming what has actually been manually verified.

The current workflow integrates Zoho retrieval, parsing, Excel writes, and a timestamp checkpoint. It has not been verified end-to-end against Zoho and the production workbook. The date search retrieves calendar-day candidates and filters them by received timestamp; verify Zoho's date-boundary behavior and timestamp field on representative messages before deployment.

`excel/writer.py` currently defines `ExcelManager`, uses `xlwings`, writes columns A–G, and saves during writes. Review its interface and resource/error handling before integrating it. The workbook sheet used by manual scripts is `MAINTENANCE DATA`. Do not infer duplicate-row policy without checking the workbook and requirements.

## Immediate next task
1. Manually verify timestamp interval resolution and Zoho received-time filtering without contacting production Zoho until explicitly requested.
2. Verify the workbook workflow using a copy and representative sanitized messages.
3. Address duplicate-write recovery after workbook save/state failure and confirm the intended most-recent-applicable-report rule against its source specification.
4. Do not perform real Zoho calls or write to the original workbook without explicit permission. Prefer sanitized fixtures and a workbook copy for initial checks.

## Environment
- Python requirement in `pyproject.toml`: `>=3.14`.
- Install the project in editable mode with `python -m pip install -e .` in the user's own environment after checking the available Python version.
- The application uses `python-dotenv`, `requests`, `xlwings`, Beautiful Soup, `lxml`, `word2number`, `dateparser`, and `rapidfuzz`.
- `.env` is local-only and must never be transferred to Codex or included in archives. Configure credentials locally from `.env.example` if needed.

## Suggested first Codex prompt
"Read `AGENTS.md`, `docs/CODEX_HANDOFF.md`, `README.md`, `docs/architecture.md`, and inspect the current Git status and implementation. Do not edit files yet. Give me a concise, evidence-based assessment of the current Phase 4/5 state, identify mismatches between docs and code, and propose the smallest next implementation step. Do not read `.env`, call Zoho, modify Excel workbooks, or discard existing changes."
