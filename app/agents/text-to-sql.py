from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.llm.model import get_model
from app.schemas.sql import SQLQuery


SYSTEM_PROMPT = """
You are a Text-to-SQL assistant.

Convert the user's natural-language question into SQL.

Rules:
- Return only valid SQL in the structured output.
- Do not invent tables or columns.
- If the database schema is not provided, make the best possible
  generic SQL assumption.
- Do not generate INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE.
- Only generate read-only SELECT queries.
"""


def generate_sql(state: AgentState) -> AgentState:
    model = get_model(provider="gemini").with_structured_output(SQLQuery)

    response = model.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", state["question"]),
        ]
    )

    return {
        "sql_query": response
    }


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("generate_sql", generate_sql)

    graph.add_edge(START, "generate_sql")
    graph.add_edge("generate_sql", END)

    return graph.compile()

graph = build_graph()

question = input("Ask your question: ")

result = graph.invoke({
        "question": question
    })

sql_query = result["sql_query"]

print("\nGenerated SQL:")
print(sql_query.sql)

print("\nExplanation:")
print(sql_query.explanation)

