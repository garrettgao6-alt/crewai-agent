# CrewAI Agent Gateway

Small CrewAI project with `intelligent_gateway.py` as the recommended main entry point.

- `intelligent_gateway.py`: recommended entry point. A JSON router agent classifies each request, then dispatches to a specialist agent. Market analysis uses Tavily search.
- `gateway.py`: simpler keyword router, useful as a lightweight fallback or comparison.
- `main.py`: fixed two-agent demo workflow for market research and executive-summary writing.

## Project Map

```text
crewai-agent/
├── .env                    # Local API keys, not committed
├── requirements.txt        # Direct project dependencies
├── intelligent_gateway.py  # Recommended main entry: JSON classifier + specialist agents
├── gateway.py              # Simple keyword-based gateway
├── main.py                 # Fixed CrewAI demo workflow
└── venv/                   # Local virtual environment
```

## Install

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configure `.env`

Create a `.env` file in this directory:

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

`OPENAI_API_KEY` is required by all three scripts. `TAVILY_API_KEY` is required by `intelligent_gateway.py` because it uses `TavilySearchTool`.

Before running a script, load the environment:

```bash
set -a
source .env
set +a
```

## Run Recommended Entry

Run the JSON router gateway:

```bash
python intelligent_gateway.py
```

This is the best default entry because it:

- classifies the user request before choosing an agent
- supports market, technical, and writing task categories
- uses Tavily search for market-analysis requests
- returns the selected specialist agent's final response

## Other Entry Points

Run the simple keyword gateway:

```bash
python gateway.py
```

Run the fixed two-agent demo workflow:

```bash
python main.py
```

## Notes

- There is no package build configuration yet; scripts are intended to be run directly.
- `venv/` is local environment state and should not be committed.
