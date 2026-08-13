from app.llm.model import get_model

def create_openrouter(model: str):
    return get_model(provider="openrouter", model=model)
