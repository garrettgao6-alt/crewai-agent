import json
import os

from openai import OpenAI


VALID_INTENTS = {"construction", "business", "general"}
DEFAULT_ROUTER_MODEL = os.getenv("OPENAI_ROUTER_MODEL", "gpt-4o-mini")

CONSTRUCTION_KEYWORDS = [
    "contract",
    "tender",
    "construction",
    "builder",
    "project",
    "scope",
]
BUSINESS_KEYWORDS = [
    "revenue",
    "strategy",
    "finance",
    "market",
    "growth",
]


def _classify_with_llm(prompt: str) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        return "general"

    client = OpenAI()
    response = client.responses.create(
        model=DEFAULT_ROUTER_MODEL,
        input=[
            {
                "role": "system",
                "content": (
                    "Classify the user's prompt into exactly one intent: "
                    "construction, business, or general. "
                    "Return JSON only, in this format: {\"intent\": \"general\"}."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    try:
        payload = json.loads(response.output_text)
    except json.JSONDecodeError:
        return "general"

    intent = str(payload.get("intent", "general")).strip().lower()
    if intent in VALID_INTENTS:
        return intent
    return "general"


def detect_intent(prompt: str) -> str:
    prompt_lower = prompt.lower()

    if any(keyword in prompt_lower for keyword in CONSTRUCTION_KEYWORDS):
        return "construction"
    if any(keyword in prompt_lower for keyword in BUSINESS_KEYWORDS):
        return "business"

    try:
        return _classify_with_llm(prompt)
    except Exception:
        return "general"
