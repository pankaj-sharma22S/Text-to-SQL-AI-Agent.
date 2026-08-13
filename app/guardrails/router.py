"""Input policy and routing decisions. Detectors are intentionally replaceable."""
from dataclasses import dataclass
from enum import Enum
import re
from langchain_core.runnables import RunnableLambda

from app.guardrails.input import InputGuardrail, InputGuardrailError


class GuardrailAction(str, Enum):
    passed = "passed"
    blocked = "blocked"
    clarification = "clarification"
    approval = "approval"


@dataclass(frozen=True)
class GuardrailDecision:
    action: GuardrailAction
    route: str
    text: str
    reason: str


class GuardrailRouter:
    _database = re.compile(r"\b(?:database|table|column|row|record|sql|query|postgres|data|count|show|list|find|how many)\b", re.I)
    _blocked = re.compile(r"\b(?:passwords?|api\s*keys?|database\s*credentials?|secrets?|private\s*keys?|credit\s*cards?|bank\s*(?:account|details)|drop\s+table|delete\s+from|truncate|update\s+.+\s+set|insert\s+into)\b", re.I)
    _ambiguous = re.compile(r"^(?:it|that|those|more|details|show me|what about)\s*[?!.]*$", re.I)
    _out_of_scope = re.compile(r"\b(?:weather|sports? scores?|news|recipe|travel|flight|shopping|stock price|send an email|execute code)\b", re.I)

    def __init__(self, detector: InputGuardrail | None = None):
        self.detector = detector or InputGuardrail()

    def evaluate(self, message: str) -> GuardrailDecision:
        checked = self.detector.process(message)
        text = checked.text
        if self._blocked.search(message):
            return GuardrailDecision(GuardrailAction.blocked, "none", text, "sensitive or dangerous request")
        if self._out_of_scope.search(message):
            return GuardrailDecision(GuardrailAction.blocked, "none", text, "request is outside the assistant scope")
        if self._ambiguous.match(message.strip()) or (self._database.search(message) and len(message.split()) < 3):
            return GuardrailDecision(GuardrailAction.clarification, "clarification", text, "request needs more context")
        route = "sql" if self._database.search(message) else "chat"
        return GuardrailDecision(GuardrailAction.passed, route, text, "request accepted")

    @staticmethod
    def trace(decision: GuardrailDecision, thread_id: str, request_id: str, model_name: str | None):
        # Only safe categorical data is sent to tracing; never the original message.
        RunnableLambda(lambda value: value).invoke(
            {"action": decision.action.value, "route": decision.route},
            config={"tags": [f"guardrail:{decision.action.value}"], "metadata": {
                "thread_id": thread_id, "request_id": request_id,
                "guardrail_reason": decision.reason, "route": decision.route,
                "model_name": model_name or "configured-model",
            }},
        )
