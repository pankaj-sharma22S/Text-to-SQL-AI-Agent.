from pydantic import BaseModel, Field
class SQLQuery(BaseModel):
    sql: str = Field(description="SQL query generated for the user's request")
    explanation: str = Field(
        description="Brief explanation of what the SQL query does"
    )