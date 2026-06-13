def review_output(text: str) -> str:
    if len(text) < 50:
        return text + "\n\n[Critic]: Response may be too short."

    return text
