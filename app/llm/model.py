import os
from dotenv import load_dotenv

load_dotenv()

def safe_provider_error(exc: Exception) -> str:
    """Convert provider failures into actionable, secret-free client messages."""
    status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
    if status == 401:
        return "LLM authentication failed. Check the provider API key and account."
    if status == 402:
        return "OpenRouter credits are exhausted. Add credits or use an API key with available credits."
    if status == 404:
        return "The configured LLM model was not found. Check OPENROUTER_MODEL."
    if status == 429:
        return "The LLM provider rate limit was reached. Try again later."
    if exc.__class__.__name__ in {"APIConnectionError", "ConnectError"}:
        return "The LLM provider could not be reached. Check network access and provider availability."
    return "The LLM provider request failed. Check provider and model configuration."

def get_model(provider: str | None = None, model: str | None = None, temperature: float = 0):
    """Create the configured chat model.

    Supported providers: ``openrouter``, ``gemini``, and ``llama``.
    ``llama`` uses Ollama locally. The provider can be passed explicitly or
    selected with LLM_PROVIDER.
    """
    selected = (provider or os.getenv("LLM_PROVIDER", "openrouter")).lower().strip()

    if selected == "openrouter":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for provider 'openrouter'")
        selected_model = model or os.getenv("OPENROUTER_MODEL")
        if not selected_model or selected_model.startswith("YOUR_"):
            raise RuntimeError("OPENROUTER_MODEL must be set to a real OpenRouter model id")
        return ChatOpenAI(
            model=selected_model,
            temperature=temperature,
            api_key=api_key,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )

    if selected == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for provider 'gemini'")
        selected_model = model or os.getenv("GEMINI_MODEL")
        if not selected_model or selected_model.startswith("YOUR_"):
            raise RuntimeError("GEMINI_MODEL must be set to a real Gemini model id")
        return ChatGoogleGenerativeAI(
            model=selected_model,
            temperature=temperature,
            google_api_key=api_key,
        )

    raise ValueError("Unsupported provider. Use only: gemini or openrouter")
