import os, sqlite3
from flask import g
from config import DATABASE, BASE_DIR

def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def init_db(app):
    with app.app_context():
        db = get_db()
        schema_path = os.path.join(BASE_DIR, "database", "schema.sql")
        with open(schema_path, encoding="utf-8") as f:
            db.executescript(f.read())
        db.commit()

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
