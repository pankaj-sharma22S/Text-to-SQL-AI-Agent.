"""Input boundary. Keep detectors replaceable so a provider can be added later."""

from dataclasses import dataclass
import os
import re


class InputGuardrailError(ValueError):
    pass


@dataclass(frozen=True)
class InputResult:
    text: str
    redacted: bool = False
    findings: tuple[str, ...] = ()


class InputGuardrail:
    """Detect injection and secrets before text can reach the LLM or database log."""

    _injection = re.compile(
        r"(?:ignore|disregard|forget)\s+(?:all|any|the|previous)\s+(?:instructions?|rules?)|"
        r"(?:reveal|show|print|repeat)\s+(?:the\s+)?(?:system|developer)\s+prompt|"
        r"(?:bypass|override|disable)\s+(?:security|guardrails?|instructions?)|"
        r"jailbreak|do\s+anything\s+now",
        re.I,
    )
    _secret_patterns = (
        ("database_url", re.compile(r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?):[^\s]+", re.I)),
        ("api_key", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[\w-]{20,}|AKIA[0-9A-Z]{16})\b")),
        ("token", re.compile(r"\b(?:bearer\s+)?[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_.-]{8,}\b", re.I)),
        ("credential", re.compile(r"\b(?:password|passwd|secret|token|api[_ -]?key)\s*[:=]\s*[^\s,;]+", re.I)),
        ("card", re.compile(r"\b(?:\d[ -]*?){13,19}\b")),
        ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)),
    )

    def __init__(self, reject_injection: bool = True, reject_secrets: bool = False):
        self.reject_injection = reject_injection
        self.reject_secrets = reject_secrets

    def process(self, text: str) -> InputResult:
        if not text or not text.strip():
            raise InputGuardrailError("Message cannot be empty")
        if self._injection.search(text) and self.reject_injection:
            raise InputGuardrailError("Request rejected by input security policy")
        findings: list[str] = []
        redacted = text
        for name, pattern in self._secret_patterns:
            if pattern.search(redacted):
                findings.append(name)
                if self.reject_secrets:
                    raise InputGuardrailError("Sensitive information must not be sent to this service")
                redacted = pattern.sub(f"[REDACTED:{name}]", redacted)
        # Catch configured credentials without ever returning their values.
        for env_name in ("DATABASE_URL", "OPENROUTER_API_KEY", "GEMINI_API_KEY"):
            value = os.getenv(env_name)
            if value and value in redacted:
                findings.append(env_name.lower())
                redacted = redacted.replace(value, f"[REDACTED:{env_name.lower()}]")
        return InputResult(redacted, bool(findings), tuple(dict.fromkeys(findings)))
