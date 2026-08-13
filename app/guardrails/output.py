"""Final redaction for values that could be returned by a database or model."""
import re

_secret = re.compile(
    r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?):[^\s]+|"
    r"(?:password|api[_ -]?key|token|secret)\s*[:=]\s*[^\s,;]+",
    re.I,
)

def sanitize_rows(rows: list[dict]) -> list[dict]:
    return [{str(k): "[REDACTED]" if _secret.search(str(v)) else v for k, v in row.items()} for row in rows]

def sanitize_answer(answer: str) -> str:
    return _secret.sub("[REDACTED]", answer or "")
