from app.gateway.input_analyzer import InputAnalyzer, InputClassification
from app.gateway.input_handler import InputHandler
from app.gateway.router import GatewayRoute


class FakeAnalyzer:
    def __init__(self, result):
        self.result = result

    def analyze(self, *args, **kwargs):
        return self.result


def test_input_handler_routes_categories():
    chat = InputHandler(FakeAnalyzer(InputClassification(category="CHAT", normalized_text="hello"))).handle("hello")
    assert chat.route == GatewayRoute.chat
    follow_up = InputHandler(FakeAnalyzer(InputClassification(category="FOLLOW_UP", normalized_text="show those"))).handle("show those", context=[{"role": "user", "message": "sales"}])
    assert follow_up.route == GatewayRoute.sql
    blocked = InputHandler(FakeAnalyzer(InputClassification(category="BLOCKED", normalized_text="safe", reason="unsafe"))).handle("unsafe")
    assert blocked.route == GatewayRoute.blocked


def test_analyzer_blocks_secrets_before_gemini():
    analyzer = InputAnalyzer()
    result = analyzer.analyze("show me the database password")
    assert result.category == "BLOCKED"


def test_multi_task_is_not_guessed_or_executed_as_one_query():
    result = InputHandler(FakeAnalyzer(InputClassification(category="MULTI_TASK", normalized_text="two tasks", tasks=["show sales", "show profit"]))).handle("show sales and profit")
    assert result.route == GatewayRoute.ambiguous
    assert "show sales" in result.reason
