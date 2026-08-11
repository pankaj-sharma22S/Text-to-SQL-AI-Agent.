import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

load_dotenv()

def get_model(provider: str | None = None, model: str | None = None, temperature: float = 0):
    """Create the configured chat model.

    Supported providers: ``openrouter``, ``gemini``, and ``llama``.
    ``llama`` uses Ollama locally. The provider can be passed explicitly or
    selected with LLM_PROVIDER.
    """
    selected = (provider or os.getenv("LLM_PROVIDER", "openrouter")).lower().strip()

    if selected == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for provider 'openrouter'")
        return ChatOpenAI(
            model=model or os.getenv("OPENROUTER_MODEL"),
            temperature=temperature,
            api_key=api_key,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )

    if selected == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for provider 'gemini'")
        return ChatGoogleGenerativeAI(
            model=model or os.getenv("GEMINI_MODEL"),
            temperature=temperature,
            google_api_key=api_key,
        )

    if selected in {"llama", "ollama"}:
        return ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=model or os.getenv("OLLAMA_MODEL"),
            temperature=temperature,
        )

    raise ValueError("Unsupported provider. Use: openrouter, gemini, or llama")
