import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

DB_PATH = BASE / os.environ.get("DB_PATH", "todo.db")
PORT = int(os.environ.get("PORT", "5000"))

app = Flask(__name__, static_folder="static", static_url_path="")

COLUMNS = "id, title, is_done, due_date, created_at, completed_at"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript((BASE / "schema.sql").read_text(encoding="utf-8"))


def error(message, status=400):
    return jsonify({"error": message}), status


def valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/todos")
def list_todos():
    sql = f"SELECT {COLUMNS} FROM todo"
    if request.args.get("filter") == "today":
        sql += " WHERE due_date = date('now','localtime') AND is_done = 0"
    sql += " ORDER BY is_done, due_date IS NULL, due_date, id"
    rows = get_db().execute(sql).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/todos")
def add_todo():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    due_date = data.get("due_date") or None
    if not title:
        return error("할 일 내용을 입력해 주세요.")
    if len(title) > 200:
        return error("할 일 내용은 200자 이하로 입력해 주세요.")
    if due_date is not None and not valid_date(due_date):
        return error("마감일은 YYYY-MM-DD 형식이어야 합니다.")

    db = get_db()
    cur = db.execute(
        "INSERT INTO todo (title, due_date) VALUES (?, ?)", (title, due_date)
    )
    db.commit()
    row = db.execute(f"SELECT {COLUMNS} FROM todo WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.patch("/api/todos/<int:todo_id>")
def update_todo(todo_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("is_done"), bool):
        return error("is_done 값(true/false)이 필요합니다.")

    db = get_db()
    cur = db.execute(
        "UPDATE todo SET is_done = ?, "
        "completed_at = CASE WHEN ? THEN datetime('now','localtime') ELSE NULL END "
        "WHERE id = ?",
        (int(data["is_done"]), int(data["is_done"]), todo_id),
    )
    db.commit()
    if cur.rowcount == 0:
        return error("해당 할 일이 없습니다.", 404)
    row = db.execute(f"SELECT {COLUMNS} FROM todo WHERE id = ?", (todo_id,)).fetchone()
    return jsonify(dict(row))


@app.delete("/api/todos/<int:todo_id>")
def delete_todo(todo_id):
    db = get_db()
    cur = db.execute("DELETE FROM todo WHERE id = ?", (todo_id,))
    db.commit()
    if cur.rowcount == 0:
        return error("해당 할 일이 없습니다.", 404)
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=PORT)
