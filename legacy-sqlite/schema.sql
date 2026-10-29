PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS todo (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  title        TEXT NOT NULL,
  is_done      INTEGER NOT NULL DEFAULT 0 CHECK (is_done IN (0,1)),
  due_date     TEXT,                       -- 'YYYY-MM-DD'
  created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_todo_due ON todo(due_date);
