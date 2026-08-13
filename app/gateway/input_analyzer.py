"""Structured, context-aware input classification before provider routing."""
from typing import Literal
from pydantic import BaseModel, Field

from app.gateway.gateway import AIGateway
from app.guardrails.input import InputGuardrail, InputGuardrailError
from app.schemas.database import DatabaseSchema

InputCategory = Literal["CHAT", "SQL", "AMBIGUOUS", "FOLLOW_UP", "MULTI_TASK", "BLOCKED", "UNKNOWN"]


class InputClassification(BaseModel):
    category: InputCategory
    normalized_text: str = Field(min_length=1)
    reason: str = Field(default="")
    clarification_question: str | None = None
    tasks: list[str] = Field(default_factory=list)


class InputAnalyzer:
    def __init__(self, gateway: AIGateway | None = None, detector: InputGuardrail | None = None):
        self.gateway = gateway or AIGateway(input_guardrail=detector)
        self.detector = detector or InputGuardrail()

    def analyze(self, message: str, context: list[dict] | None = None, schema: DatabaseSchema | None = None) -> InputClassification:
        checked = self.detector.process(message)
        lower = checked.text.lower()
        # Secrets and injection are rejected before any classifier call.
        if any(term in lower for term in ("password", "api key", "credential", "secret", "private key", "credit card", "bank account")):
            return InputClassification(category="BLOCKED", normalized_text=checked.text, reason="sensitive information request")
        if any(term in lower for term in ("drop table", "delete from", "truncate", "insert into", "update ", "alter table", "grant ", "revoke ")):
            return InputClassification(category="BLOCKED", normalized_text=checked.text, reason="dangerous SQL request")

        schema_text = schema.to_prompt() if schema else "No schema available. Do not infer database entities."
        context_text = str((context or [])[-6:])
        prompt = (
            "Classify the user input. Support English, Hindi, and Hinglish, including spelling mistakes. "
            "Normalize Hindi/Hinglish into concise English in normalized_text. Use conversation context for FOLLOW_UP. "
            "Use MULTI_TASK when there are multiple independent requests and list each task. "
            "Use AMBIGUOUS when required meaning is missing; never guess. Use UNKNOWN when classification is unsafe or unclear. "
            "Never invent tables or columns. Return only the requested structured JSON.\n"
            f"Schema:\n{schema_text}\nContext:\n{context_text}\nInput:\n{checked.text}"
        )
        try:
            result = self.gateway.invoke_sync(
                "gemini",
                [("system", "You are a safe multilingual input classifier."), ("human", prompt)],
                structured=InputClassification,
            )
            return result
        except Exception:
            return InputClassification(category="UNKNOWN", normalized_text=checked.text, reason="classifier unavailable")
