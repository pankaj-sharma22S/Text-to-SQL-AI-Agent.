from app.tools.database_server import get_checkpoint_url

def test_checkpoint_url_uses_psycopg_format(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost/db")
    assert get_checkpoint_url() == "postgresql://user:pass@localhost/db"
