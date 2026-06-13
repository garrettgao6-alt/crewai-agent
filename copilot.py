import os

from openai import OpenAI


DEFAULT_COPILOT_MODEL = os.getenv("OPENAI_COPILOT_MODEL", "gpt-4o-mini")


def run_copilot(user_input: str) -> str:
    cleaned_input = user_input.strip()
    if not cleaned_input:
        raise ValueError("Copilot input is required.")

    client = OpenAI()
    response = client.responses.create(
        model=DEFAULT_COPILOT_MODEL,
        input=cleaned_input,
    )
    return response.output_text
