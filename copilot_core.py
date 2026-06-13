from core.engine import run_engine


def run_copilot(prompt: str, user_id: str = "default") -> str:
    return run_engine(user_id, prompt)
