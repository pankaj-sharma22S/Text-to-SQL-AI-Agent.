"""Parser-backed SQL policy and query risk analysis."""

from enum import Enum
import re
from pydantic import BaseModel, Field
from app.schemas.database import DatabaseSchema


class SQLValidationError(ValueError):
    pass


class HumanApprovalRequired(SQLValidationError):
    pass


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class QueryRisk(BaseModel):
    requires_approval: bool = False
    risk_level: RiskLevel = RiskLevel.low
    reason: str = ""
    findings: list[str] = Field(default_factory=list)


class SQLSecurityGateway:
    forbidden = re.compile(r"\b(?:insert|update|delete|drop|alter|truncate|create|grant|revoke|merge|call|copy|do|vacuum|refresh)\b", re.I)

    def validate(self, sql: str, schema: DatabaseSchema) -> QueryRisk:
        query = sql.strip()
        if not query or ";" in query.rstrip(";") or query.endswith(";") and ";" in query[:-1]:
            raise SQLValidationError("SQL must contain exactly one statement")
        if not re.match(r"^(?:select|with)\b", query, re.I) or self.forbidden.search(query):
            raise SQLValidationError("Only read-only SELECT/WITH SQL is allowed")
        tables = {t.name.lower(): t for t in schema.tables}
        referenced_tables, referenced_columns = self._references(query)
        unknown = sorted(t for t in referenced_tables if t not in tables and t not in {"unnest"})
        if unknown:
            raise SQLValidationError("Unknown table(s): " + ", ".join(unknown))
        known_columns = {c.name.lower() for t in schema.tables for c in t.columns}
        unknown_columns = sorted(c for c in referenced_columns if c not in known_columns and c not in {"*", "true", "false"})
        if unknown_columns:
            raise SQLValidationError("Unknown column(s): " + ", ".join(unknown_columns))
        risk = self.analyze(query, schema, referenced_tables)
        if risk.requires_approval:
            raise HumanApprovalRequired(risk.reason)
        return risk

    def _references(self, sql: str) -> tuple[set[str], set[str]]:
        # sqlglot is the preferred parser; the fallback remains conservative and dependency-light.
        try:
            import sqlglot
            from sqlglot import exp
            statements = sqlglot.parse(sql, read="postgres")
            if len(statements) != 1:
                raise SQLValidationError("SQL must contain exactly one statement")
            root = statements[0]
            if not isinstance(root, (exp.Select, exp.Union, exp.With)) and not root.find(exp.Select):
                raise SQLValidationError("Only SELECT/WITH SQL is allowed")
            tables = {x.name.lower() for x in root.find_all(exp.Table) if x.name}
            columns = {x.name.lower() for x in root.find_all(exp.Column) if x.name and not x.is_star}
            return tables, columns
        except ImportError:
            tokens = re.findall(r"\b[a-zA-Z_][\w$]*\b", sql.lower())
            keywords = {"select", "from", "where", "and", "or", "as", "on", "join", "left", "right", "inner", "outer", "group", "by", "order", "limit", "offset", "having", "with", "asc", "desc", "null", "is", "not", "in", "like", "distinct", "case", "when", "then", "else", "end", "count", "sum", "avg", "min", "max", "true", "false"}
            matches = re.findall(r"\b(?:from|join)\s+([a-zA-Z_]\w*)", sql, re.I)
            aliases = re.findall(r"\b(?:from|join)\s+[a-zA-Z_]\w*(?:\s+as)?\s+([a-zA-Z_]\w*)", sql, re.I)
            table_names = {x.lower() for x in matches}
            return table_names, {x for x in tokens if x not in keywords and x not in table_names and x not in {a.lower() for a in aliases}}

    def analyze(self, sql: str, schema: DatabaseSchema, tables: set[str] | None = None) -> QueryRisk:
        findings: list[str] = []
        upper = sql.upper()
        if re.search(r"SELECT\s+\*", sql, re.I) and not re.search(r"\bLIMIT\s+\d+", sql, re.I):
            findings.append("SELECT * without LIMIT")
        if tables and len(tables) > 1:
            findings.append("multiple table query")
        if len(re.findall(r"\bJOIN\b", upper)) >= 2:
            findings.append("multiple joins")
        if re.search(r"\b(?:GROUP\s+BY|DISTINCT|COUNT\s*\(|SUM\s*\(|AVG\s*\()", upper) and "LIMIT" not in upper:
            findings.append("unbounded aggregation")
        if tables and not re.search(r"\bWHERE\b", upper) and len(tables) >= 1:
            findings.append("unfiltered table scan")
        if findings:
            level = RiskLevel.high if len(findings) >= 2 else RiskLevel.medium
            return QueryRisk(requires_approval=level == RiskLevel.high, risk_level=level, reason="; ".join(findings), findings=findings)
        return QueryRisk()
