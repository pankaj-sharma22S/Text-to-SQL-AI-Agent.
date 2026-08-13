from app.schemas.database import DatabaseSchema

class SchemaMetadata:
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
        self.tables = {table.name.lower(): table for table in schema.tables}
        self.columns = {table.name.lower(): {column.name.lower() for column in table.columns} for table in schema.tables}

    def matches_terms(self, text: str) -> bool:
        words = {word.lower() for word in text.split()}
        return bool(words & set(self.tables) or any(words & cols for cols in self.columns.values()))

    def ambiguity_reason(self, text: str) -> str | None:
        lower = text.lower()
        if "best" in lower or "top" in lower or "successful" in lower:
            measures = [c.name for table in self.schema.tables for c in table.columns if any(x in c.name.lower() for x in ("revenue", "profit", "sales", "count", "amount"))]
            if len(measures) > 1:
                return "The request has multiple possible measures: " + ", ".join(measures[:5])
        return None
