from app.llm.model import get_model

def create_gemini(model: str):
    return get_model(provider="gemini", model=model)
