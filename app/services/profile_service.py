import asyncio
from sqlalchemy import text
from app.api.schemas.profile import UserProfile

class ProfileService:
    def __init__(self, engine): self.engine = engine

    def ensure_table(self):
        with self.engine.begin() as c:
            c.execute(text("CREATE TABLE IF NOT EXISTS user_profile (id INTEGER PRIMARY KEY CHECK (id = 1), data JSONB NOT NULL)"))

    async def get(self):
        def query():
            with self.engine.connect() as c:
                row = c.execute(text("SELECT data FROM user_profile WHERE id = 1")).scalar_one_or_none()
                return UserProfile.model_validate(row or {})
        return await asyncio.to_thread(query)

    async def update(self, profile: UserProfile):
        data = profile.model_dump_json()
        def write():
            with self.engine.begin() as c:
                c.execute(text("INSERT INTO user_profile(id, data) VALUES (1, CAST(:data AS JSONB)) ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data"), {"data": data})
        await asyncio.to_thread(write)
        return profile
