from app.schemas.database import DatabaseSchema, TableInfo, ColumnInfo
from app.schemas.sql import SQLQuery, MemoryUpdate, ConversationMessage
from app.tools.database_server import get_checkpoint_url

def test_models_and_prompt():
    schema = DatabaseSchema(tables=[TableInfo(name="users", columns=[ColumnInfo(name="id", data_type="INTEGER")], primary_keys=["id"])])
    assert "TABLE: users" in schema.to_prompt()
    assert SQLQuery(sql="SELECT 1", explanation="constant").sql.startswith("SELECT")
    assert MemoryUpdate().preferences == []
    assert ConversationMessage(thread_id="t1", role="user", message="hello").role == "user"
