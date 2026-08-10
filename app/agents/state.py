from typing import TypedDict
from app.schemas.sql import SQLQuery


class AgentState(TypedDict, total=False):
    question: str
    sql_query: SQLQuery