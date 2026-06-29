# AEGIS Email Disclosure Analysis

## Status
Design — approved 2026-06-28.

## Goal
Allow anyone to email a criminal disclosure (as attachments and/or inline body text) to a single AEGIS inbox hosted on the RunPod instance, have it analysed by the existing defence-analysis pipeline, and receive a DOCX brief back by email.

## Scope
- Inbound IMAP polling + outbound SMTP replies using Python stdlib.
- Reuse existing AEGIS parsing, ingestion, analysis, and export components.
- SQLite job store for status and audit.
- FastAPI admin endpoints and a Streamlit "Email Inbox" page.
- Single inbound account, single-pod deployment, disabled by default.

Out of scope for MVP:
- Multiple inbound accounts, Microsoft Graph, webhooks, Redis/Celery queue, reply-all, thread merging.
- These are explicitly noted as future extensions.

## Background
AEGIS already exposes a complete disclosure-analysis pipeline through `POST /api/v1/analyse/disclosure`:

1. `core/file_parser.py::FileParser` extracts text from PDF/DOCX/DOC/TXT/XLSX/HTML/MD/CSV/JSON.
2. Ingestion stores chunks in a ChromaDB `temp_session_<id>` collection.
3. `core/agent_swarm.py::AgentSwarm.analyse_disclosure()` runs the 6-KC swarm.
4. `core/report_export.py::build_docx()` produces the legal brief.

There is currently no email integration. This design adds a minimal email bridge that sits beside the existing API and reuses that pipeline.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Protocol | Generic IMAP/SMTP | Works with Gmail, Outlook, and standard providers without new SDKs. |
| Deployment model | FastAPI lifespan poller | Matches the existing `_cleanup_temp_collections_task` pattern; no new infrastructure. |
| Job persistence | SQLite file in `tenant_data/email_jobs.db` | Durable, queryable, no extra service. |
| Analysis tenant | System/internal tenant | Isolates emailed disclosures from registered tenant data. |
| Collections | `temp_session_email_<job_id>` | Reuses existing temp collection lifecycle and cleanup. |
| Concurrency | Shared analysis semaphore | Protects GPU from concurrent analysis regardless of entry point. |
| IMAP read flag | Set only on success | Failed jobs remain unread and are retried automatically. |
| Output | DOCX attached, short body | Body states the report is attached and includes the standard disclaimer. |
| Reply target | Original sender only | Privacy and simplicity. |
| Default state | Disabled unless configured | Safe for existing deployments. |

## Architecture

```
┌─────────────┐     IMAP      ┌──────────────────┐
│   Sender    │ ─────────────>│  email_client    │
│  (anyone)   │               │  (imaplib)       │
└─────────────┘               └────────┬─────────┘
                                       │
                                       v
                              ┌──────────────────┐
                              │  email_poller    │
                              │  (asyncio task)  │
                              └────────┬─────────┘
                                       │
                                       v
                              ┌──────────────────┐
                              │  email_processor │
                              └────────┬─────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           v                           v                           v
   ┌───────────────┐         ┌─────────────────┐         ┌──────────────┐
   │  FileParser   │         │  AgentSwarm     │         │ ReportExport │
   │  (existing)   │         │  (existing)     │         │  (existing)  │
   └───────────────┘         └─────────────────┘         └──────────────┘
                                       │                           │
                                       v                           v
                              ┌─────────────────┐         ┌──────────────┐
                              │  ChromaDB temp  │         │ DOCX/PDF/TXT │
                              │  collection     │         │ brief        │
                              └─────────────────┘         └──────┬───────┘
                                                                 │
                                                                 v SMTP
                                                          ┌─────────────┐
                                                          │   Sender    │
                                                          └─────────────┘
```

## Components

### `services/email_config.py`
- Read and validate environment variables.
- Provide typed `EmailConfig` dataclass.
- Expose `is_enabled()` and `is_healthy()` helpers.

Required env vars when enabled:
- `AEGIS_EMAIL_POLLER_ENABLED=true`
- `AEGIS_EMAIL_IMAP_HOST`
- `AEGIS_EMAIL_IMAP_PORT` (default 993)
- `AEGIS_EMAIL_IMAP_USE_SSL` (default true)
- `AEGIS_EMAIL_IMAP_USERNAME`
- `AEGIS_EMAIL_IMAP_PASSWORD`
- `AEGIS_EMAIL_SMTP_HOST`
- `AEGIS_EMAIL_SMTP_PORT` (default 587)
- `AEGIS_EMAIL_SMTP_USE_TLS` (default true)
- `AEGIS_EMAIL_SMTP_USERNAME`
- `AEGIS_EMAIL_SMTP_PASSWORD`
- `AEGIS_EMAIL_INBOX_NAME` (default INBOX)

Optional:
- `AEGIS_EMAIL_POLL_INTERVAL_SECONDS` (default 60)
- `AEGIS_EMAIL_MAX_RETRIES` (default 3)
- `AEGIS_EMAIL_SENDER_DAILY_LIMIT` (default 10)
- `AEGIS_EMAIL_MAX_ATTACHMENT_BYTES` (default 25 MB)
- `AEGIS_EMAIL_DRY_RUN` (default false)
- `AEGIS_EMAIL_SYSTEM_TENANT_ID` (default `system_email`)

### `services/email_client.py`
- `ImapClient`: connect, list unseen, fetch message, mark read.
- `SmtpClient`: send reply with text body and attachment.
- Support SSL and STARTTLS variants.
- All operations use timeouts.

### `services/email_job_store.py`
- SQLite schema:
  - `id` (UUID primary key)
  - `message_id` (unique IMAP Message-ID)
  - `sender` (from address)
  - `subject`
  - `received_at`
  - `attachment_count`
  - `status` (`received`, `parsing`, `analysing`, `completed`, `failed`, `quarantined`)
  - `retry_count`
  - `result_path`
  - `error_message`
  - `updated_at`
- Functions: `create_job`, `get_job`, `list_jobs`, `update_status`, `increment_retry`, `get_counts`.

### `services/email_processor.py`
- `process_email(raw_message)`:
  1. Parse MIME message with `email.message_from_bytes`.
  2. Skip inline attachments.
  3. Decode body text (plain + HTML fallback).
  4. Save attachments to temp directory.
  5. Validate content exists and is parseable; reject password-protected files.
  6. Call `FileParser.parse_multiple()`.
  7. Ingest into `temp_session_email_<job_id>` collection.
  8. Acquire analysis semaphore; call `AgentSwarm.analyse_disclosure()`.
  9. Build DOCX as `AEGIS_Disclosure_Analysis_<job_id>_<timestamp>.docx`; fallback to PDF, then plain text.
  10. Send reply via SMTP.
  11. Mark IMAP message read.
- `process_batch(messages)`: iterate, catch exceptions, update job store.

### `services/email_poller.py`
- `start_poller(app_state)` registered in `api/server.py` lifespan.
- Loop:
  1. Sleep `AEGIS_EMAIL_POLL_INTERVAL_SECONDS`.
  2. If not enabled, skip.
  3. Connect IMAP, fetch unseen messages.
  4. Call `email_processor.process_batch()`.
  5. Disconnect cleanly.
- Network errors are logged but do not mark jobs failed.

### `api/email_routes.py`
- `GET /api/v1/email/health` — test IMAP/SMTP connectivity.
- `POST /api/v1/email/fetch` — manually trigger one poll cycle.
- `GET /api/v1/email/jobs` — list jobs; query params: `status`, `since`, `limit`, `offset`.
- `GET /api/v1/email/jobs/{id}` — job detail.
- `POST /api/v1/email/jobs/{id}/retry` — retry a failed/quarantined job.
- `GET /api/v1/email/metrics` — counts by status.

### Streamlit UI
New page in `web/streamlit_app.py`:
- Default view: jobs from last 7 days.
- Filters: status, date range.
- Actions: manual fetch, retry selected job.
- Detail modal: sender, subject, status, attachments, error, download result.

## Data Flow

1. Sender emails disclosure to the configured AEGIS inbox.
2. Poller fetches unseen messages every 60 seconds.
3. A job record is created with status `received`, deduped by Message-ID.
4. Attachments and body text are extracted and parsed.
5. Parsed text is ingested into a temp ChromaDB collection.
6. Analysis runs under the shared GPU semaphore.
7. DOCX/PDF/TXT brief is generated.
8. Reply is sent to the original sender with subject `AEGIS Disclosure Analysis: <original subject>`, a short body with disclaimer, and the DOCX/PDF/TXT brief attached.
9. IMAP message is marked read; job status becomes `completed`.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| IMAP/SMTP network error | Log, leave messages unread, retry next poll. |
| No attachments and empty body | Send failure notice; mark read; status `failed`. |
| All attachments unparseable or password-protected | Send failure notice; mark read; status `failed`. |
| Analysis/export failure | Increment retry; if under limit, leave unread; else send failure notice and mark `quarantined`. |
| SMTP send failure after successful analysis | Mark `failed`; retry later; do not regenerate report if it exists. |
| Dry-run enabled | Analyse but do not send; log intended reply; mark read. |
| Duplicate Message-ID | Skip; return existing job. |
| Sender exceeds daily limit | Reply with rate-limit notice; mark read; status `quarantined`. |

## Testing

- Unit tests:
  - Config validation (enabled/disabled states, missing vars).
  - IMAP client with mocked `imaplib`.
  - SMTP client with mocked `smtplib`.
  - Job store CRUD and deduplication.
  - Processor attachment extraction and validation.
- Integration tests:
  - End-to-end processor flow using a sample `.eml` file and mocked LLM/RAG.
  - Poller loop with fake IMAP client.
- Regression:
  - Ensure existing `/api/v1/analyse/disclosure` behaviour unchanged.

## Security & Operations

- Credentials stored in environment variables for MVP.
- Feature disabled by default (`AEGIS_EMAIL_POLLER_ENABLED`).
- Per-sender daily rate limit.
- Max attachment size enforced before parsing.
- Runs under isolated system tenant.
- Logs written to `logs/email_poller.log` and existing app logging.

## Future Extensions

- Multi-account support via tenant-scoped config.
- Microsoft Graph / webhook-based ingestion.
- Redis + Celery/RQ worker queue for reliability and scale.
- Thread-aware merging for multi-email disclosures.
- OCR for image-based disclosures.
- Encrypted credential storage (Fernet).

## Acceptance Criteria

- [ ] With valid IMAP/SMTP config, the poller fetches unseen emails every 60 seconds.
- [ ] Emails with parseable attachments or body text produce a DOCX brief and SMTP reply.
- [ ] Emails with no usable content receive a polite failure reply.
- [ ] Failed jobs retry up to the configured limit, then become quarantined.
- [ ] Successful jobs mark the IMAP message as read.
- [ ] Admin endpoints return job lists, detail, and metrics.
- [ ] Streamlit page displays recent jobs and supports manual fetch/retry.
- [ ] All new code covered by unit + integration tests.
- [ ] Existing `/api/v1/analyse/disclosure` endpoint continues to pass regression tests.
