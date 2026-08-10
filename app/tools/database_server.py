import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)


def execute_sql(query: str):
    with engine.connect() as connection:
        result = connection.execute(text(query))

        rows = [dict(row._mapping) for row in result]

        return rows