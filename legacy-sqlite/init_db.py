import os
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent


def load_env(path):
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


env = load_env(BASE / ".env")
db_path = BASE / os.environ.get("DB_PATH", env.get("DB_PATH", "todo.db"))

with sqlite3.connect(db_path) as conn:
    conn.executescript((BASE / "schema.sql").read_text(encoding="utf-8"))

print(f"DB 준비 완료: {db_path}")
