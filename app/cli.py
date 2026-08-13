import logging, os, uuid
from dotenv import load_dotenv
from sqlalchemy import text
from app.tools.database_server import get_engine, get_checkpoint_url, is_mysql_url
from app.schemas.sql import ConversationMessage

load_dotenv(); logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def ensure_memory_table(engine):
    if is_mysql_url():
        with engine.begin() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS conversations (thread_id VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL, message TEXT NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
            c.execute(text("CREATE TABLE IF NOT EXISTS text_to_sql_memory (thread_id VARCHAR(255) PRIMARY KEY, data JSON NOT NULL)"))
        return
    with engine.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS conversations (thread_id TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), message TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        c.execute(text("CREATE TABLE IF NOT EXISTS text_to_sql_memory (thread_id TEXT PRIMARY KEY, data JSONB NOT NULL)"))

def save_message(engine, message: ConversationMessage):
    with engine.begin() as c:
        c.execute(text("INSERT INTO conversations(thread_id, role, message) VALUES (:thread_id, :role, :message)"), message.model_dump(exclude_none=True))

def show_history(engine, thread_id=None):
    query = "SELECT thread_id, role, message, created_at FROM conversations"
    params = {}
    if thread_id:
        query += " WHERE thread_id = :thread_id"; params["thread_id"] = thread_id
    query += " ORDER BY created_at, thread_id"
    with engine.connect() as c: rows = c.execute(text(query), params).mappings().all()
    if not rows: print("No conversation history found."); return
    for row in rows: print(f"[{row['created_at']}] {row['thread_id']} {row['role']}: {row['message']}")

def run():
    from app.agents.graph import build_graph
    url = os.getenv("DATABASE_URL")
    if not url: raise RuntimeError("DATABASE_URL is required")
    engine = get_engine(); ensure_memory_table(engine)
    if is_mysql_url():
        raise RuntimeError("The terminal CLI requires PostgreSQL checkpoint storage; use the FastAPI server with MySQL.")
    from langgraph.checkpoint.postgres import PostgresSaver
    with PostgresSaver.from_conn_string(get_checkpoint_url()) as saver:
        saver.setup(); graph = build_graph(saver); thread_id = None
        print("Text-to-SQL terminal. Commands: new, list, history, history <thread_id>, continue <thread_id>, exit")
        while True:
            command = input("\n> ").strip()
            if command.lower() == "exit": break
            if command.lower() == "new":
                thread_id = str(uuid.uuid4()); logging.info("thread created: %s", thread_id); print(f"Thread: {thread_id}"); continue
            if command.lower() == "list":
                with engine.connect() as c:
                    rows = c.execute(text("SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id")).scalars().all()
                print("\n".join(rows) or "No conversations"); continue
            if command.lower() == "history": show_history(engine); continue
            if command.lower().startswith("history "): show_history(engine, command.split(None, 1)[1].strip()); continue
            if command.lower().startswith("continue "):
                thread_id = command.split(None, 1)[1].strip(); print(f"Continuing: {thread_id}"); continue
            if not thread_id:
                print("Create or continue a thread first."); continue
            save_message(engine, ConversationMessage(thread_id=thread_id, role="user", message=command))
            config = {"configurable": {"thread_id": thread_id}}
            result = graph.invoke({"question": command}, config)
            print("\n" + result["answer"])
            save_message(engine, ConversationMessage(thread_id=thread_id, role="assistant", message=str(result["answer"])))
            if result.get("memory"):
                with engine.begin() as c:
                    c.execute(text("INSERT INTO text_to_sql_memory(thread_id,data) VALUES (:id, CAST(:data AS JSONB)) ON CONFLICT (thread_id) DO UPDATE SET data = text_to_sql_memory.data || EXCLUDED.data"), {"id": thread_id, "data": result["memory"].model_dump_json()})

if __name__ == "__main__": run()
