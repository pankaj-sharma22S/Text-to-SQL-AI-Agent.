from typing import Annotated, TypedDict
import operator
from app.schemas.sql import SQLQuery, MemoryUpdate
from app.schemas.database import DatabaseSchema



class AgentState(TypedDict, total=False):
    question: str
    sql_query: SQLQuery
    schema: DatabaseSchema
    rows: list[dict]
    answer: str
    memory: MemoryUpdate
    error: str
    retry_count: int
    history: Annotated[list[dict], operator.add]
