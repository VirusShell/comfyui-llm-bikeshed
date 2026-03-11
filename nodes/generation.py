"""Generation nodes for LLM text generation."""


def _build_messages(system_prompt: str, prompt: str) -> list[dict]:
    """Build message list for LLM chat completion.

    Args:
        system_prompt: System prompt text. Omitted from messages if empty.
        prompt: User prompt text. Always included.

    Returns:
        List of message dicts with 'role' and 'content' keys.
    """
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages
