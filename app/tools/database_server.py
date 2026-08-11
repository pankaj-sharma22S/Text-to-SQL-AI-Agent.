import os
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
from app.schemas.database import DatabaseSchema, TableInfo, ColumnInfo, ForeignKeyInfo

load_dotenv()

def get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    return create_engine(url, pool_pre_ping=True)

def discover_schema(engine=None) -> DatabaseSchema:
    engine = engine or get_engine()
    inspector = inspect(engine)
    tables = []
    for name in inspector.get_table_names():
        columns = [ColumnInfo(name=c["name"], data_type=str(c["type"]),
                    nullable=c.get("nullable", True), default=str(c["default"]) if c.get("default") else None)
                    for c in inspector.get_columns(name)]
        pk = inspector.get_pk_constraint(name).get("constrained_columns") or []
        fks = [ForeignKeyInfo(column=col, referenced_table=f["referred_table"], referenced_column=ref)
               for f in inspector.get_foreign_keys(name)
               for col, ref in zip(f.get("constrained_columns", []), f.get("referred_columns", []))]
        tables.append(TableInfo(name=name, columns=columns, primary_keys=pk, foreign_keys=fks))
    return DatabaseSchema(tables=tables)

def execute_sql(query: str, engine=None):
    if not query.lstrip().lower().startswith(("select", "with", "show", "explain")):
        raise ValueError("Only read-only SELECT/WITH/SHOW/EXPLAIN queries are allowed")
    with (engine or get_engine()).connect() as connection:
        return [dict(row._mapping) for row in connection.execute(text(query))]
