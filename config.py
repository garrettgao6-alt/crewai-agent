import logging
import os
from pathlib import Path

from langchain_openai import ChatOpenAI

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


logger = logging.getLogger(__name__)


def load_environment():
    if load_dotenv is not None:
        load_dotenv(Path(__file__).resolve().parent / ".env")
    else:
        logger.warning("python-dotenv is not installed; .env auto-load skipped.")


def create_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )


def build_search_tools():
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("TAVILY_API_KEY is not set; Tavily search disabled.")
        return []

    try:
        from crewai_tools import TavilySearchTool
    except ImportError:
        logger.warning("crewai_tools.TavilySearchTool is unavailable; Tavily search disabled.")
        return []

    try:
        return [TavilySearchTool()]
    except Exception as exc:
        logger.warning(
            "TavilySearchTool initialization failed; Tavily search disabled. Details: %s",
            exc,
        )
        return []
