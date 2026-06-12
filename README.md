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
```

`intelligent_gateway.py` automatically loads `.env` from the project directory. You do not need to manually `source .env`.

`TAVILY_API_KEY` is optional. When it is missing, or when `TavilySearchTool` cannot be imported or initialized, the gateway logs a warning and disables search instead of failing startup.

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

The sidebar is organized into `Prompt Library`, `Form Builder`, `Document Analysis`, `Project Intelligence Review`, and `History` sections. The SQLite-backed Prompt Library section lets you choose a `Business` or `Construction` category, select a prompt, and click `Load Template` to place the full template into the editable input box. The prompt text remains editable before submitting.

The Form Builder section is collapsed by default and covers all Business and Construction prompt templates. Choose a form category and template, complete the structured fields, and click `Generate Prompt` to write a professional prompt into the same editable input box. Form fields support text inputs, larger text areas, dropdowns, and multi-select focus areas.

The Document Analysis section is collapsed by default and supports single-file PDF, TXT, DOCX, and XLSX uploads. Choose an analysis type, upload a document, and click `Generate Document Prompt` to place the extracted document text and requested analysis task into the editable input box. Uploaded content is limited to the first 12000 characters when needed, and the generated prompt states when truncation occurred.

The Project Intelligence Review section is collapsed by default and supports multi-file project reviews for construction and business workflows. Upload multiple project documents, choose a review type, and click `Generate Project Review Prompt` to combine the extracted content into one professional cross-document review prompt.

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

Clicking `Generate Prompt` updates `st.session_state.query`; the user can still edit the generated prompt before submitting it in Fast Mode or Advanced Agent Routing.

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

After a Document Analysis result is generated, the result area shows a `Download PDF` button. PDF export uses `reportlab`, preserves line breaks, paginates long reports, and names the file from the selected analysis type, such as `contract_review.pdf` or `business_analysis.pdf`.

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
