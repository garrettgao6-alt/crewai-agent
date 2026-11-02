# CrewAI Agent Gateway

Small CrewAI project with `intelligent_gateway.py` as the recommended main entry point.

The gateway classifies each user request as `market`, `technical`, or `writing`, then dispatches it to the matching specialist agent. Market analysis can use Tavily search when `TAVILY_API_KEY` is configured; if Tavily is missing or unconfigured, the gateway still starts and runs without search tools.

## Project Structure

```text
crewai-agent/
├── .env.example              # Example local environment configuration
├── .dockerignore             # Docker build exclusions
├── .github/workflows/ci.yml  # GitHub Actions CI
├── Dockerfile                # FastAPI container image definition
├── agents.py                 # Agent factory definitions
├── api.py                    # FastAPI HTTP gateway
├── config.py                 # Environment, LLM, and Tavily setup
├── intelligent_gateway.py    # Recommended CLI entry point
├── gateway.py                # Legacy simple keyword gateway
├── main.py                   # Legacy fixed demo workflow
├── prompt_store.py           # SQLite prompt library setup and query helpers
├── prompts.db                # SQLite prompt library database
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Test/development dependencies
├── run_local.sh              # Local script that starts FastAPI and Streamlit
├── streamlit_app.py          # Streamlit web UI for the FastAPI gateway
├── user_store.py             # Local account store, password hashing, and account limits
├── test_gateway_routing.py   # Pytest routing and error-handling tests
└── README.md
```

## Install

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

Install development dependencies when running tests locally:

```bash
python -m pip install -r requirements-dev.txt
```

## Configure `.env`

Copy the example file and fill in your local values:

```bash
cp .env.example .env
```

Required:

```env
OPENAI_API_KEY=your_openai_api_key
```

Optional:

```env
TAVILY_API_KEY=your_tavily_api_key
LOG_LEVEL=INFO
OTEL_SDK_DISABLED=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me
MAX_USERS=3
```

`intelligent_gateway.py` automatically loads `.env` from the project directory. You do not need to manually `source .env`.

`TAVILY_API_KEY` is optional. When it is missing, or when `TavilySearchTool` cannot be imported or initialized, the gateway logs a warning and disables search instead of failing startup.

`ADMIN_USERNAME` and `ADMIN_PASSWORD` are used only to create the first local admin account when `users.db` is empty. Set a strong admin password in your real `.env`; the default example password is not hard-coded in the application. `MAX_USERS` controls active local accounts. `MAX_USERS=3` allows up to three active users, and `MAX_USERS=0` allows unlimited users.

## Run

Run the recommended JSON router gateway:

```bash
python intelligent_gateway.py
```

This entry point:

- loads `.env` automatically
- creates the shared OpenAI LLM client
- creates Tavily search tools when available
- creates router, market, technical, and writing agents
- classifies each request before choosing a specialist agent
- falls back to the writing agent if routing fails
- returns a friendly error if the specialist LLM call fails

Start the local FastAPI and Streamlit development servers together:

```bash
./run_local.sh
```

The script checks that `.env` and `venv` exist before starting services. FastAPI runs on `http://127.0.0.1:8000`, Streamlit runs on `http://127.0.0.1:8501`, and pressing `Ctrl+C` stops both.

Run the FastAPI gateway locally:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Analyze request:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"用户问题"}'
```

Run the Streamlit web UI in a second terminal after FastAPI is running:

```bash
streamlit run streamlit_app.py
```

The Streamlit app displays `category`, `confidence`, `version`, `result`, and response time fields. It also keeps a session-local History sidebar with the 10 most recent requests, including each request's query, mode, routing metadata, result, and elapsed time. Use `Clear History` to reset the sidebar.

The Streamlit UI uses a premium SaaS design for a scientific intelligence platform, with a responsive desktop and mobile layout, a mobile contrast fix for Safari and Android Chrome, a refined hero section, a Mobile Quick Guide, scientific module cards, polished sidebar sections, and a card-based report area with metadata metrics. The sidebar is organized into `Prompt Library`, `Form Builder`, `Document Intelligence`, `Executive Intelligence Center`, `Automation Intelligence`, and `Intelligence History` sections. The SQLite-backed Prompt Library section lets you choose a `Business` or `Construction` category, select a prompt, and click `Load Prompt Template` to place the full template into the editable input box. The prompt text remains editable before submitting.

The Mobile Quick Guide appears below the hero section as a compact `📱 Mobile Quick Guide` expander. It gives iPhone and Android users a clear onboarding path: open the sidebar, select a tool, generate a prompt, submit the analysis, and download the PDF report.

The app requires local account authentication before the workspace is available. Users can sign in or create an account with username/email and password. Passwords are hashed with `hashlib.pbkdf2_hmac` and stored in `users.db`; the local database is ignored by git so real user records are not committed. New registrations require a unique username, a unique email address, matching password confirmation, and a password of at least eight characters.

Local accounts are limited by `MAX_USERS`, which defaults to `3`. The app counts active users only. When the active user count reaches the configured limit, registration is blocked with `Account limit reached. Please contact the administrator.` Set `MAX_USERS=0` to remove the account limit.

The app includes subscription and usage management for commercial plans. New local accounts start on `Starter`, and the sidebar shows the current plan, monthly AI request usage, monthly document analysis usage, and renewal date. Usage is stored in `users.db` and resets when the monthly subscription period renews.

Subscription tiers:

- Starter: $19/month, 100 AI requests/month, 20 document analyses/month, PDF export, basic automation templates.
- Professional: $49/month, 1000 AI requests/month, 200 document analyses/month, multi-document analysis, Executive Intelligence, full Automation Intelligence.
- Business: $149/month, 5000 AI requests/month, 1000 document analyses/month, API access, team accounts for 20 users, priority support.
- Enterprise: custom pricing, unlimited*, dedicated support, custom deployment.

When a user reaches a monthly limit, the UI blocks the action and displays: `You have reached your monthly plan limit. Upgrade your subscription to continue.` Stripe fields are reserved in `users.db` as `stripe_customer_id` and `stripe_subscription_id`, but Stripe checkout and billing are not connected yet.

The Form Builder section is collapsed by default and covers all Business and Construction prompt templates. Choose a form category and template, complete the structured fields, and click `Generate Professional Prompt` to write a professional prompt into the same editable input box. Form fields support text inputs, larger text areas, dropdowns, and multi-select focus areas.

The Document Intelligence section is collapsed by default and supports single-file PDF, TXT, DOCX, and XLSX uploads. Choose an analysis type, upload a document, and click `Generate Document Intelligence Prompt` to place the extracted document text and requested analysis task into the editable input box. Uploaded content is limited to the first 12000 characters when needed, and the generated prompt states when truncation occurred.

The Executive Intelligence Center section is collapsed by default and supports multi-file project reviews for construction and business workflows. Upload multiple project documents, choose a review type and agent mode, then click `Generate Executive Review` to combine the extracted content into one professional cross-document review prompt. Click `Run Executive Agent Team` to run the selected CrewAI executive agent workflow and save the board-level result to History.

The Automation Intelligence section is collapsed by default and generates practical automation blueprints, workflow plans, SOPs, calendars, tables, and campaign structures. Choose an automation type, complete the targeted fields, and click `Generate Automation Blueprint` to write a complete professional prompt into the editable input box.

Streamlit supports two modes:

- Fast Mode: enabled by default. It skips the Router Agent and runs the Writer Agent directly from the UI process.
- Advanced Agent Routing: posts requests to `http://127.0.0.1:8000/analyze` and uses the existing Router Agent to choose the specialist agent.

The FastAPI route contract is unchanged. The CLI behavior in `intelligent_gateway.py` is unchanged.

## Prompt Library

Prompt templates are stored in `prompts.db` using SQLite. The `prompts` table contains:

- `id`
- `category`
- `name`
- `content`
- `version`
- `created_at`
- `updated_at`

If `prompts.db` does not exist, `prompt_store.py` automatically creates it and seeds the default Business and Construction templates. Future template management can be added through `prompt_store.py` without changing `api.py`, `intelligent_gateway.py`, or `run_local.sh`.

## Form Builder

The Streamlit Form Builder is defined in `streamlit_app.py` through a `FORM_LIBRARY` configuration. It covers the same Business and Construction template areas as the Prompt Library, but uses structured fields and targeted dropdowns to generate prompts consistently.

Supported field types:

- `text_input`
- `text_area`
- `selectbox`
- `multiselect`

Clicking `Generate Professional Prompt` updates `st.session_state.query`; the user can still edit the generated prompt before submitting it in Fast Mode or Advanced Agent Routing.

## Document Analysis

Document Analysis reads one uploaded file in the Streamlit sidebar and generates a document-specific analysis prompt. Each analysis type uses its own professional report structure instead of a shared generic checklist.

Supported formats:

- PDF through `pypdf`
- TXT through UTF-8 decoding
- DOCX through `python-docx`
- XLSX through `openpyxl`

Supported analysis types:

- Contract Review
- Tender Review
- Risk Assessment
- Meeting Minutes
- Progress Report
- Safety Inspection
- Business Analysis

Uploaded document content is limited to the first 12000 extracted characters. The UI shows the extracted character count and truncation status.

After a Document Analysis result is generated, the result area shows a `Download Report PDF` button. PDF export uses `reportlab`, preserves line breaks, paginates long reports, and names the file from the selected analysis type, such as `contract_review.pdf` or `business_analysis.pdf`.

## Project Intelligence Review

Project Intelligence Review is a commercial multi-document workflow for project-level analysis. It supports multiple PDF, TXT, DOCX, and XLSX uploads in one review and preserves each file name in the generated prompt.

Supported review types:

- Full Project Review
- Contract + Tender Review
- Commercial Risk Review
- Construction Risk Review
- NCC / Compliance Review
- Procurement Review
- Progress & Meeting Review

Each uploaded file is limited to the first 12000 extracted characters, and combined project document content is limited to 30000 characters. Files that cannot be read show an error and are skipped without blocking other uploaded files.

## Executive Agent Team

`executive_agents.py` defines a real CrewAI executive review team that analyzes uploaded project document text without Tavily search. The team includes Contract, Tender, Risk, NCC Compliance, Finance, BIM, and Executive Coordinator agents. Each agent has its own role, goal, backstory, and task, and the Executive Coordinator combines the specialist outputs into a board-level report.

The Streamlit UI keeps the generated executive review prompt editable, and `Run Executive Agent Team` executes the multi-agent workflow directly from the Executive Intelligence Center section. Executive results are saved to History and support `Download Report PDF`.

Executive agent modes:

- Fast Executive Review: runs only the Executive Coordinator Agent for the fastest, lowest-cost review.
- Full Board Review: runs Contract, Risk, Finance, and Executive Coordinator agents for balanced speed and quality.
- Deep Due Diligence: runs Contract, Tender, Risk, NCC, Finance, BIM, and Executive Coordinator agents for the strongest analysis.

History entries and exported Executive PDFs include the selected `agent_mode`.

## Automation Intelligence

Automation Intelligence is defined in `streamlit_app.py` through an `AUTOMATION_LIBRARY` configuration. It generates complete prompts for practical automation planning while keeping the final prompt editable before submission.

Supported automation types:

- Project management automation
- Gantt chart planning
- Social media scheduling planner
- Market research automation
- Repetitive task automation
- Data analysis and visualization
- Office automation
- File organization automation
- Promotion email automation

Each automation type has targeted fields, a dedicated prompt template, required output sections, and required table formats. Generated prompts can produce automation blueprints, workflow plans, SOPs, checklists, reports, dashboard plans, content calendars, email campaign plans, and Gantt chart plans.

Current automation scope:

- Generates automation blueprint, workflow, SOP, report, table, calendar, or campaign planning prompts.
- Does not automatically publish social media posts.
- Does not automatically send emails.
- Does not connect to or call Gmail, Outlook, Buffer, Zapier, Make, or social media APIs.
- Does not scrape images, contacts, or audience lists.
- Does not save third-party account passwords.
- Requires human review before publishing, sending, or executing any automation workflow.

## Docker

Build the image:

```bash
docker build -t crewai-agent .
```

Run the container with local environment variables:

```bash
docker run --env-file .env -p 8000:8000 crewai-agent
```

Check the container health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

The Docker build excludes `.env`, local virtual environments, caches, and git metadata through `.dockerignore`.

## VPS Production Run

For a VPS deployment where Gao Intelligence Hub must keep running after SSH disconnects and automatically recover after server restarts, install the systemd services in `deploy/`.

Expected production path:

```text
/root/crewai-agent
```

Before installing services, make sure the project is deployed at that path, `.env` is configured, dependencies are installed into `venv`, and the app can start manually.

Install systemd services:

```bash
sudo bash deploy/install_systemd.sh
```

The installer:

- copies `deploy/garrett-api.service` to `/etc/systemd/system/`
- copies `deploy/garrett-streamlit.service` to `/etc/systemd/system/`
- runs `systemctl daemon-reload`
- enables both services at boot
- restarts both services
- prints status and log commands

Check service status:

```bash
systemctl status garrett-api
systemctl status garrett-streamlit
```

Restart services:

```bash
systemctl restart garrett-api
systemctl restart garrett-streamlit
```

View live logs:

```bash
journalctl -u garrett-api -f
journalctl -u garrett-streamlit -f
```

Service details:

- FastAPI runs on `127.0.0.1:8000`
- Streamlit runs on `0.0.0.0:8501`
- Streamlit uses `API_URL=http://127.0.0.1:8000/analyze`
- both services use `Restart=always` and `RestartSec=5`

## Tests

Run the local test suite:

```bash
python -m pytest -q
```

Run syntax compilation checks:

```bash
python -m py_compile intelligent_gateway.py config.py agents.py api.py streamlit_app.py prompt_store.py test_gateway_routing.py test_api.py
```

The routing tests mock `crewai` and `langchain_openai` before importing `intelligent_gateway.py`, so tests do not call real OpenAI or Tavily services.

## GitHub Actions

CI is defined in `.github/workflows/ci.yml`.

On every push and pull request, GitHub Actions:

- sets up Python 3.12
- installs `requirements.txt`
- installs `requirements-dev.txt`
- runs `py_compile`
- runs `pytest`
- uses test environment variables instead of real API keys

## Legacy Entry Points

`intelligent_gateway.py` is the only recommended entry point.

The older scripts are kept for comparison and demos:

- `gateway.py`: simple keyword-based gateway
- `main.py`: fixed two-agent demo workflow

These legacy scripts do not receive the same routing, logging, fallback, and test coverage as `intelligent_gateway.py`.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

## Deployment reliability

The `Deploy` workflow runs Python 3.12 regression tests and dependency checks on Ubuntu 24.04 before a production job can start. Pull requests run tests only. Pushes to `main` deploy the exact tested commit; manual runs default to a read-only `verify` operation, with explicit `backup` and `deploy` choices. An older rerun cannot replace a newer `main` release. Deployment failures remain failures; no error is hidden or marked successful.

`SERVER_SSH_KEY` must contain the complete, unencrypted deployment private key. The corresponding public key must already be authorized for the intended deployment account on the current server. The workflow prints only its public fingerprint and public key in the job summary, so administrators can compare identities without exposing the private key. Empty, malformed, encrypted or rejected keys stop before application/data changes. Password prompts and unrelated agent identities are disabled. A server migration requires checking the address, authorized deployment identity and host identity together.

The SSH host-key digest in `deploy/github_release.sh` was read from the authenticated DigitalOcean console. A scanned host key is accepted only when its digest matches that pin; host verification is never disabled. If the host key changes, verify the replacement independently through the console before updating the pin. Do not replace the pin with an unverified network scan. Keep production backups and rollback behavior in `deploy/production_release.sh`; service health and real server acceptance must succeed before a release is recorded.

## Server-local NCC references

Set `NCC_DOCUMENT_ROOT` to an existing server directory, for example
`/srv/gaointelligence/ncc`, and grant the Streamlit and API service users read
access to its PDF/TXT documents. Both services must use the same root and
application directory. Place only reference documents intended for application
users inside this directory; all signed-in users can select paths within it.
Do not put credentials or private customer documents in this shared root.

After signing in, open **Settings → Server NCC references**. Save either a
relative path within the root (for example `2022/volume-one`) or an absolute
path inside it, together with the correct edition and volume. Settings are
persisted per account in `ncc_library.db`; preserve that file across deployments.
A directory includes its immediate PDF/TXT files, without recursive traversal.
The limits are 100 files, 50 MB per file, and 100 MB total. PDFs need an
extractable text layer; scanned documents need OCR first.

NCC/compliance queries combine locally matched code references with the current
project's uploaded NCC references and project evidence. File size and
modification time invalidate the in-process text cache. Citations include the
configured edition, filename, page, and detected clause identifier. Relevant
excerpts are sent to the configured AI provider during analysis; saving a path
alone sends no document contents. Retrieval is a reference aid and does not
establish which NCC edition applies to a project. If no keyword matches are
found, the local library contributes no evidence.

The website cannot read paths on a visitor's computer. Paths must exist on the
server. Symlinks and paths that resolve outside `NCC_DOCUMENT_ROOT` are rejected.
Use **Disable local NCC references** to stop using a saved path without deleting
any server documents.

## Project isolation and durable reports (v2)

The Streamlit application and `/analyze` API now validate project ownership
before analysis. Uploaded documents and conversation memory use a canonical
user-and-project namespace. Project history and report reads/writes also require
the owner identity; there is no implicit administrator bypass or team sharing.
Switching projects clears the previous project's UI history and upload widgets.
Legacy user-only indexes and memory are not automatically assigned to projects:
re-import documents into the correct project after verifying their ownership.
No legacy data is deleted by this upgrade.

Authentication cookies now hold opaque server-side session tokens, stored as
hashes with seven-day expiry in `users.db`. Sign-out revokes the current token.
Old user-ID cookies are no longer accepted, so existing users must sign in again.
Set a strong `COOKIE_SECRET_KEY`; when no non-placeholder key is configured,
the app atomically generates a private `.cookie_secret` file. Preserve that file
and `users.db` across deployments. Sessions are revalidated on each Streamlit
script pass; inactive accounts and revoked/expired sessions are rejected.

The analysis API requires `Authorization: Bearer <session token>` and a JSON
body with `query` and `project_id`. It does not accept a caller-supplied user ID.
Missing/invalid sessions return 401; inaccessible projects/reports return 404.
The Streamlit login issues these tokens; this release does not add an external
API-token management console. `/analyze` returns the saved report ID, project,
full result, source snapshots, status, and version. This is an intentional API
contract change from the previous unprotected gateway.

Automatic and explicit NCC ingestion now use the same project-scoped code
collection. Clause identifiers such as C2D2, D2D3, H1D2 and C1.1 are recognized;
PDF page numbers and original-document SHA-256 hashes are preserved. Enter the
actual edition/volume when importing code documents. Unrecognized clause layout
falls back to searchable page text without inventing clause numbers. Re-uploading
a filename replaces the previous version within that project after successful
indexing. A provider failure does not erase the preceding index. Ingestion
replacement is serialized within a single application process; multiple ingestion
workers need a shared job lock before horizontal scaling.

Model embedding failures now return an explicit error rather than silently
switching vector dimensions. Fresh v2 project namespaces require successful
embedding calls before indexing. Standard NCC queries merge relevant regulations
and project evidence; requests without a regulatory reference return an explicit
`insufficient_evidence` result. Local reference keyword search includes a small
Chinese construction-term glossary; it is not a full multilingual semantic engine.
Neither an edition label nor a matching passage proves regulatory applicability.

Each analysis returns its own evidence directly, without reading a process-global
citation list. A context-local compatibility accessor remains for older internal
callers. Full report text, owner/project, timestamp, status, source metadata,
verbatim excerpts and snapshot hashes are stored in `reports.db`. Reports remain
available in a new session after selecting the project, and the Reports page
exports PDF for Copilot reports too. Later document replacement does not mutate
saved report evidence. Reports remain drafts for human review; placeholder AUTO
risk/recommendations and the old fixed report-section messages have been removed.

Back up `users.db`, `projects.db`, `reports.db`, `ncc_library.db`, `memory.db`,
`chroma_db/`, the NCC reference directory and the encryption secret before release.
Keep these on persistent storage. Install the updated requirements and restart
both services; the existing deploy.sh does not install dependency updates.
Schema additions are automatic and additive. Validate with:

```bash
python -m pytest -q
```

`test_project_integrity.py` exercises real temporary SQLite/Chroma storage,
parallel analyses, project authorization, document replacement, report restore,
and Streamlit Copilot-to-report/PDF flow. Model responses and embeddings are
controlled test substitutes; production model quality and capacity need separate
acceptance testing with approved reference documents.

### Managed documents and IFC data checks

The active Documents page retains project-owned PDF/TXT/DOCX/XLSX originals in `project_documents/` with an immutable version registry in `documents.db`. Preserve both during backup and restore. Versions use checksummed private storage; the server never creates a public original-file URL. Downloads use five-minute, single-use server tickets bound to the active account session and project. Revoked sessions and expired/used tickets cannot download files. Account session tokens are never placed in URLs. Existing indexes without originals remain searchable and are disclosed separately; their lost originals cannot be reconstructed.

Successful new versions consume one monthly document allowance; an identical active upload is idempotent. Failed or interrupted processing preserves the preceding active version and refunds its document allowance once. AI token reservations remain spent according to the existing conservative budget policy. Per-account file operations are serialized across processes. Search excludes failed, archived and superseded versions; one analysis retains one version manifest, and existing report evidence is unchanged. Archive/unarchive and restoring retained versions do not permanently delete files or make new embedding calls.

Limits are 50 MB per document, 80 KB of extracted text, 60 chunks, and 600 MB/1,000 retained versions per account. Embeddings for a managed document are sent as one bounded batch. Office expanded sizes, cell count, parser time and worker memory are bounded. Scanned PDFs require OCR before indexing; an unsupported scan is marked failed rather than indexed successfully. DOCX body/table text and XLSX sheet/cell text are read; formulas are not recalculated and extracted section numbers do not reproduce Office pagination.

BIM Model Checks parses actual IFC STEP files with [IfcOpenShell](https://docs.ifcopenshell.org/ifcopenshell-python.html). Signed-in projects can inspect identifiers, length units, spatial containment, representation availability, overall door/window dimensions and placements. Findings link to IFC entity IDs/GlobalIds. The original, inspection JSON and a draft report persist under project authorization; CSV exports neutralize spreadsheet formulas. Repeating the identical active model does not charge or save twice. This local inspection uses zero AI tokens and one document allowance for a successful new model version.

BIM limits: 20 MB, 100,000 entity records, 20,000 elements, a 40-second worker deadline, and 1,000 exported issue rows/dimension samples with explicit truncation. These are data-quality checks, not tessellated geometry, clash detection, quantity take-off, Revit/Navisworks processing or NCC certification. Overall dimensions are not verified clear-opening widths. Guest BIM examples continue to use a clearly identified synthetic issue log and cannot access private files or invoke private model processing.


### Responsive interface and interactive workflows

The active web UI uses one responsive theme in `ui_theme.py`, visible page shortcuts, a home logo, and a shared authorized project picker. Workflow selection prepares an editable Copilot draft; only explicit review submission calls AI. Changing project clears drafts, conversation history and report search. Dashboard workflow expansion, filename/report search, BIM severity/check/element filters, real processing status, and recoverable empty states use native controls. Download links retain the existing short-lived server authorization. Upload buttons disable oversized files before processing. Mobile layouts wrap navigation and metric cards; hover/focus feedback and entrance/loading motion respect reduced-motion preferences. Theme and navigation changes do not alter storage, ownership or AI budgets.

## Public search and answer-engine content

`public_site.py` builds English product guides under `/discover/`, with canonical metadata, visible FAQ answers, matching JSON-LD and a public-only sitemap. It imports no application stores. The workspace remains at `/`; Nginx sends `X-Robots-Tag: noindex, nofollow, noarchive` for app and private routes. Indexing controls supplement authentication and do not replace project access checks. No search rank, FAQ rich result or AI citation is promised.

`deploy/install_public_seo.py BACKUP_DIR` snapshots Nginx configuration and the current public release before an atomic static release. It checks Nginx and live content, restoring on failure. The production release also restores this snapshot if later acceptance fails. Public files are generated separately from application uploads and credentials. To recover manually: `venv/bin/python BACKUP_DIR/public-seo-state/restore.py BACKUP_DIR --restore`.

Review public feature statements when changing product capabilities; update `REVIEWED` only after reviewing that content. Validate with `python -m unittest test_public_seo`. Submit `https://www.gaointelligence.com/sitemap.xml` through an already verified search-console property when available.

Social sharing uses only fixed public guide URLs, never the current workspace URL, query parameters, account details or report contents. Each guide has its own 1200×630 PNG, matching Open Graph/X metadata, manual copy fallback and share-composer links. A 1080×1080 home image is provided for social posts. The tiny first-party sharing script loads no third-party widgets and makes no network requests. Browser/device sharing opens a user-controlled destination; the app never posts automatically.

The Nginx homepage snippet inserts generic public product metadata into the existing Streamlit HTML shell for all visitors and user agents. It preserves the workspace and its noindex policy, and requires the already enabled Nginx HTTP substitution module. It disables upstream compression for this shell so substitution is reliable. The snippet is included in backup and rollback. Versioned social asset URLs avoid reusing the earlier generic preview cache; third-party platforms can still retain old previews until they re-fetch the URL.
