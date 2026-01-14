"""LLM client utilities for LangChain integration."""

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def get_llm(model: str | None = None, temperature: float = 0.1) -> ChatOpenAI:
    """
    Get configured LLM instance for LangChain chains.

    Args:
        model: Model name override (defaults to config setting)
        temperature: Temperature for generation (default 0.1)

    Returns:
        ChatOpenAI instance configured with API key and model
    """
    settings = get_settings()

    # Use provided model or fall back to config default
    model_name = model or settings.OPENAI_MODEL

    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=model_name,
        temperature=temperature,
    )
