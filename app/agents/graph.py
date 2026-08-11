import logging
from langgraph.graph import StateGraph, START, END
from app.agents.state import AgentState
from app.llm.model import get_model
from app.schemas.sql import SQLQuery, MemoryUpdate
from app.tools.database_server import discover_schema, execute_sql, get_engine

log = logging.getLogger(__name__)
SYSTEM = """You are a read-only PostgreSQL Text-to-SQL assistant. Use only this schema:
{schema}
Return SQLQuery. Generate only SELECT or WITH queries; never modify data."""

def load_schema(state):
    log.info("loading schema")
    return {"schema": discover_schema()}

def generate_sql(state):
    log.info("generating SQL")
    prompt = SYSTEM.format(schema=state["schema"].to_prompt())
    response = get_model().with_structured_output(SQLQuery).invoke([
        ("system", prompt), ("human", "Conversation context:\n" + str(state.get("history", [])) + "\nQuestion: " + state["question"])
    ])
    return {"sql_query": response, "retry_count": state.get("retry_count", 0)}

def validate_sql(state):
    sql = state["sql_query"].sql.strip().lower()
    if not sql.startswith(("select", "with")) or ";" in sql[:-1]:
        raise ValueError("Generated SQL must be a single read-only SELECT/WITH statement")
    return {}

def execute(state):
    log.info("executing SQL")
    try:
        return {"rows": execute_sql(state["sql_query"].sql), "error": ""}
    except Exception as exc:
        log.exception("SQL execution failed")
        return {"error": str(exc), "retry_count": state.get("retry_count", 0) + 1}

def route_execution(state):
    return "retry" if state.get("error") and state.get("retry_count", 0) < 2 else "answer"

def answer(state):
    if state.get("error"):
        result = "SQL execution failed after limited retries: " + state["error"]
        return {"answer": result, "history": [{"user": state["question"], "assistant": result}]}
    response = get_model().invoke([("system", "Answer concisely using the SQL result."), ("human", f"Question: {state['question']}\nRows: {state.get('rows', [])}")])
    return {"answer": response.content, "history": [{"user": state["question"], "assistant": response.content}]}

def memory(state):
    response = get_model().with_structured_output(MemoryUpdate).invoke([
        ("system", "Extract only durable preferences, facts, or important context. Use empty lists if none."),
        ("human", state["question"] + "\n" + state.get("answer", ""))])
    return {"memory": response}

def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    for name, fn in [("load_schema", load_schema), ("generate_sql", generate_sql), ("validate_sql", validate_sql), ("execute", execute), ("answer", answer), ("memory", memory)]: graph.add_node(name, fn)
    graph.add_edge(START, "load_schema"); graph.add_edge("load_schema", "generate_sql"); graph.add_edge("generate_sql", "validate_sql"); graph.add_edge("validate_sql", "execute")
    graph.add_conditional_edges("execute", route_execution, {"retry": "generate_sql", "answer": "answer"})
    graph.add_edge("answer", "memory"); graph.add_edge("memory", END)
    return graph.compile(checkpointer=checkpointer)
