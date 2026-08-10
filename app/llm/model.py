import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

load_dotenv()


def get_model(provider: str, model: str | None = None, temperature: float = 0):
    """
    Create an LLM from Gemini, OpenRouter, or Ollama.
    """

    provider = provider.lower()

    # -------------------------
    # GEMINI
    # -------------------------
    if provider == "gemini":

        return ChatGoogleGenerativeAI(
            model=model or "gemini-2.5-flash",
            temperature=temperature,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )

    # -------------------------
    # OPENROUTER
    # -------------------------
    elif provider == "openrouter":

        return ChatOpenAI(
            model=model or "openai/gpt-4o-mini",
            temperature=temperature,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    # -------------------------
    # OLLAMA
    # -------------------------
    elif provider == "ollama":

        return ChatOllama(
            model=model or "qwen2.5-coder:7b",
            temperature=temperature,
        )

    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            "Use: gemini, openrouter, or ollama."
        )