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
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Test/development dependencies
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

The Streamlit app displays `category`, `confidence`, `version`, and `result` fields.

Streamlit supports two modes:

- Fast Mode: enabled by default. It skips the Router Agent and runs the Writer Agent directly from the UI process.
- Advanced Agent Routing: posts requests to `http://127.0.0.1:8000/analyze` and uses the existing Router Agent to choose the specialist agent.

The FastAPI route contract is unchanged. The CLI behavior in `intelligent_gateway.py` is unchanged.

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
python -m py_compile intelligent_gateway.py config.py agents.py api.py streamlit_app.py test_gateway_routing.py test_api.py
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
