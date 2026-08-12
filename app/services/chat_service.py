import asyncio
import logging
import uuid
from sqlalchemy import text
from app.schemas.sql import ConversationMessage
from app.tools.database_server import get_engine, get_checkpoint_url
from app.cli import ensure_memory_table, save_message

log = logging.getLogger(__name__)

class ChatService:
    def __init__(self, graph, engine):
        self.graph = graph
        self.engine = engine

    @classmethod
    def create(cls, graph=None):
        from app.agents.graph import build_graph
        from langgraph.checkpoint.postgres import PostgresSaver
        saver = PostgresSaver.from_conn_string(get_checkpoint_url()).__enter__()
        saver.setup()
        engine = get_engine(); ensure_memory_table(engine)
        return cls(graph or build_graph(saver), engine)

    def create_conversation(self):
        return str(uuid.uuid4())

    async def chat(self, thread_id: str, message: str):
        await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="user", message=message))
        try:
            result = await asyncio.to_thread(self.graph.invoke, {"question": message}, {"configurable": {"thread_id": thread_id}})
        except Exception:
            log.exception("chat failed for thread %s", thread_id)
            raise
        answer = str(result["answer"])
        await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="assistant", message=answer))
        return answer

    async def stream_chat(self, thread_id: str, message: str):
        await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="user", message=message))
        answer = None
        config = {"configurable": {"thread_id": thread_id}}
        try:
            async for event in self.graph.astream_events({"question": message}, config, version="v2"):
                kind = event.get("event")
                if kind == "on_chain_end" and event.get("name") == "answer":
                    output = event.get("data", {}).get("output", {})
                    answer = str(output.get("answer", ""))
                    yield {"event": "answer", "data": answer}
                elif kind == "on_chain_start" and event.get("name") in {"load_schema", "generate_sql", "validate_sql", "execute", "answer", "memory"}:
                    yield {"event": "status", "data": event["name"]}
            if answer is None:
                raise RuntimeError("LangGraph completed without an answer")
            await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="assistant", message=answer))
            yield {"event": "done", "data": thread_id}
        except Exception:
            log.exception("streaming chat failed for thread %s", thread_id)
            raise

    async def list_conversations(self):
        def query():
            with self.engine.connect() as c:
                rows = c.execute(text("""SELECT thread_id,
                    MIN(message) FILTER (WHERE role = 'user') AS title,
                    (array_agg(message ORDER BY created_at DESC))[1] AS preview,
                    MAX(created_at) AS updated_at
                    FROM conversations GROUP BY thread_id ORDER BY updated_at DESC""")).mappings().all()
                return [{**dict(row), "updated_at": row["updated_at"].isoformat()} for row in rows]
        return await asyncio.to_thread(query)

    async def history(self, thread_id=None):
        def query():
            sql = "SELECT thread_id, role, message, created_at FROM conversations"
            params = {}
            if thread_id: sql += " WHERE thread_id = :thread_id"; params["thread_id"] = thread_id
            sql += " ORDER BY created_at, thread_id"
            with self.engine.connect() as c: return [dict(row) for row in c.execute(text(sql), params).mappings().all()]
        return await asyncio.to_thread(query)

    async def delete_conversation(self, thread_id):
        def delete():
            with self.engine.begin() as c:
                c.execute(text("DELETE FROM conversations WHERE thread_id = :id"), {"id": thread_id})
                c.execute(text("DELETE FROM text_to_sql_memory WHERE thread_id = :id"), {"id": thread_id})
                for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                    c.execute(text(f"DELETE FROM {table} WHERE thread_id = :id"), {"id": thread_id})
        await asyncio.to_thread(delete)
