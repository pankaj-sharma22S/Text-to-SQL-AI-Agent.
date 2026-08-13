"""Boundary handler that turns input classification into a safe routing decision."""
from dataclasses import dataclass
import uuid

from app.gateway.input_analyzer import InputAnalyzer, InputClassification
from app.gateway.router import GatewayRoute
from app.schemas.database import DatabaseSchema


@dataclass(frozen=True)
class InputHandlingResult:
    category: str
    route: GatewayRoute
    text: str
    reason: str
    request_id: str
    tasks: tuple[str, ...] = ()


class InputHandler:
    def __init__(self, analyzer: InputAnalyzer | None = None):
        self.analyzer = analyzer or InputAnalyzer()

    def handle(self, message: str, context: list[dict] | None = None, schema: DatabaseSchema | None = None) -> InputHandlingResult:
        result: InputClassification = self.analyzer.analyze(message, context=context, schema=schema)
        route = self._route(result, context)
        reason = result.reason or result.clarification_question or result.category.lower()
        if result.category == "MULTI_TASK" and result.tasks:
            reason = "Please handle these tasks separately: " + "; ".join(result.tasks)
        return InputHandlingResult(
            category=result.category,
            route=route,
            text=result.normalized_text,
            reason=reason,
            request_id=str(uuid.uuid4()),
            tasks=tuple(result.tasks),
        )

    @staticmethod
    def _route(result: InputClassification, context) -> GatewayRoute:
        if result.category == "BLOCKED":
            return GatewayRoute.blocked
        if result.category == "AMBIGUOUS" or result.category == "UNKNOWN":
            return GatewayRoute.ambiguous
        if result.category == "CHAT":
            return GatewayRoute.chat
        if result.category in {"SQL", "FOLLOW_UP"}:
            return GatewayRoute.sql
        if result.category == "MULTI_TASK":
            return GatewayRoute.ambiguous
        return GatewayRoute.ambiguous
