import asyncio
import logging
import uuid
import os
from sqlalchemy import text
from app.schemas.sql import ConversationMessage
from app.tools.database_server import get_engine, get_checkpoint_url, is_mysql_url
from app.cli import ensure_memory_table, save_message
from app.guardrails.input import InputGuardrail
from app.guardrails.output import sanitize_answer
from app.guardrails.router import GuardrailAction
from app.agents.chat_node import chat_node, fast_chat_response
from app.gateway.gateway import AIGateway
from app.gateway.input_handler import InputHandler
from app.gateway.input_analyzer import InputAnalyzer
from app.tools.database_server import discover_schema

log = logging.getLogger(__name__)

class ChatService:
    def __init__(self, graph, engine, input_guardrail=None, guardrail_router=None, gateway=None, input_handler=None):
        self.graph = graph
        self.engine = engine
        self.input_guardrail = input_guardrail or InputGuardrail()
        self.gateway = gateway or AIGateway(input_guardrail=self.input_guardrail)
        self.input_handler = input_handler or InputHandler(InputAnalyzer(gateway=self.gateway, detector=self.input_guardrail))

    @staticmethod
    def _model_name():
        return os.getenv("OPENROUTER_MODEL") or os.getenv("GEMINI_MODEL") or os.getenv("OLLAMA_MODEL") or "configured-model"

    @classmethod
    def create(cls, graph=None):
        from app.agents.graph import build_graph
        if is_mysql_url():
            # langgraph-checkpoint-postgres cannot use MySQL. Keep the graph unchanged
            # and use an in-process checkpoint until a MySQL saver is selected.
            from langgraph.checkpoint.memory import InMemorySaver
            saver = InMemorySaver()
        else:
            from langgraph.checkpoint.postgres import PostgresSaver
            saver = PostgresSaver.from_conn_string(get_checkpoint_url()).__enter__()
            saver.setup()
        engine = get_engine(); ensure_memory_table(engine)
        return cls(graph or build_graph(saver), engine)

    def create_conversation(self):
        return str(uuid.uuid4())

    async def chat(self, thread_id: str, message: str):
        request_id = str(uuid.uuid4())
        schema = await asyncio.to_thread(discover_schema, self.engine)
        context = await self.history(thread_id)
        decision = self.input_handler.handle(message, context=context, schema=schema)
        if not (decision.route == "chat" and fast_chat_response(decision.text)):
            log.info("gateway request_id=%s route=%s reason=%s", decision.request_id, decision.route, decision.reason)
        if decision.route.value == "blocked":
            raise InputGuardrailError("Request blocked by security policy")
        if decision.route.value == "ambiguous":
            answer = str((await self.gateway.clarify(decision.text, decision.reason, thread_id)).content)
            await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="user", message=decision.text))
            await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="assistant", message=answer))
            return answer
        message = decision.text
        await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="user", message=message))
        try:
            config = {"configurable": {"thread_id": thread_id}, "tags": ["guardrail:passed"], "metadata": {"thread_id": thread_id, "request_id": request_id, "route": decision.route, "model_name": self._model_name()}}
            if decision.route == "chat":
                result = await asyncio.to_thread(chat_node, {"question": message}, config, self.gateway)
            else:
                result = await asyncio.to_thread(self.graph.invoke, {"question": message}, config)
        except Exception:
            log.exception("chat failed for thread %s", thread_id)
            raise
        answer = sanitize_answer(str(result["answer"]))
        await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="assistant", message=answer))
        return answer

    async def stream_chat(self, thread_id: str, message: str):
        request_id = str(uuid.uuid4())
        schema = await asyncio.to_thread(discover_schema, self.engine)
        context = await self.history(thread_id)
        decision = self.input_handler.handle(message, context=context, schema=schema)
        if not (decision.route == "chat" and fast_chat_response(decision.text)):
            log.info("gateway request_id=%s route=%s reason=%s", decision.request_id, decision.route, decision.reason)
        if decision.route.value == "blocked":
            raise InputGuardrailError("Request blocked by security policy")
        message = decision.text
        await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="user", message=message))
        if decision.route.value == "ambiguous":
            answer = str((await self.gateway.clarify(decision.text, decision.reason, thread_id)).content)
            await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="assistant", message=answer))
            yield {"event": "answer", "data": answer}
            yield {"event": "done", "data": thread_id}
            return
        if decision.route == "chat":
            config = {"tags": ["guardrail:passed"], "metadata": {"thread_id": thread_id, "request_id": request_id, "route": "chat", "model_name": self._model_name()}}
            answer = sanitize_answer(str((await asyncio.to_thread(chat_node, {"question": message}, config, self.gateway))["answer"]))
            await asyncio.to_thread(save_message, self.engine, ConversationMessage(thread_id=thread_id, role="assistant", message=answer))
            yield {"event": "answer", "data": answer}
            yield {"event": "done", "data": thread_id}
            return
        answer = None
        config = {"configurable": {"thread_id": thread_id}, "tags": ["guardrail:passed"], "metadata": {"thread_id": thread_id, "request_id": request_id, "route": "sql", "model_name": self._model_name()}}
        try:
            async for event in self.graph.astream_events({"question": message}, config, version="v2"):
                kind = event.get("event")
                if kind == "on_chain_end" and event.get("name") == "answer":
                    output = event.get("data", {}).get("output", {})
                    answer = sanitize_answer(str(output.get("answer", "")))
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
                sql = """SELECT thread_id,
                    MIN(message) FILTER (WHERE role = 'user') AS title,
                    (array_agg(message ORDER BY created_at DESC))[1] AS preview,
                    MAX(created_at) AS updated_at
                    FROM conversations GROUP BY thread_id ORDER BY updated_at DESC"""
                if self.engine.dialect.name == "mysql":
                    sql = """SELECT thread_id,
                        MIN(CASE WHEN role = 'user' THEN message END) AS title,
                        SUBSTRING_INDEX(GROUP_CONCAT(message ORDER BY created_at DESC), ',', 1) AS preview,
                        MAX(created_at) AS updated_at
                        FROM conversations GROUP BY thread_id ORDER BY updated_at DESC"""
                rows = c.execute(text(sql)).mappings().all()
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
