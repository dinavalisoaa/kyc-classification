"""Local DB (SQLite): tracks documents received from the papi API (label, split,
download status). Replaces guessing the client group by regex on the filename --
the train/val split is computed once per client_id and stays stable.
"""
import hashlib
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get('DB_PATH', 'documents.db')
VAL_RATIO = 0.2

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,          -- id provided by the papi API
    path TEXT NOT NULL,              -- CDN path, e.g. /uploads/cin_xxx.jpg
    type TEXT NOT NULL,              -- label: cin, photo, residence, statuts, cif, stat
    client_id TEXT NOT NULL,         -- group for the train/val split
    split TEXT NOT NULL,             -- 'train' or 'val', assigned once per client_id
    local_path TEXT,                 -- local path once downloaded (NULL until then)
    downloaded_at TEXT               -- download timestamp (NULL if not done yet)
);
CREATE INDEX IF NOT EXISTS idx_documents_downloaded ON documents(downloaded_at);
"""


@contextmanager
def connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path=DB_PATH):
    with connection(db_path) as conn:
        conn.executescript(SCHEMA)


def split_for_client(client_id):
    # Deterministic split per client: same client -> always same split, no train/val leak.
    h = int(hashlib.md5(client_id.encode()).hexdigest(), 16)
    return 'val' if (h % 100) < VAL_RATIO * 100 else 'train'


def upsert_documents(documents, db_path=DB_PATH):
    """documents: list of dicts {id, path, type, client_id} from the papi API.
    Does not overwrite local_path/downloaded_at if the document is already known."""
    with connection(db_path) as conn:
        for d in documents:
            conn.execute("""
                INSERT INTO documents (id, path, type, client_id, split)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    path=excluded.path, type=excluded.type, client_id=excluded.client_id
            """, (d['id'], d['path'], d['type'], d['client_id'],
                  split_for_client(d['client_id'])))


def documents_to_download(db_path=DB_PATH):
    with connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(
            'SELECT * FROM documents WHERE downloaded_at IS NULL')]


def mark_downloaded(doc_id, local_path, db_path=DB_PATH):
    with connection(db_path) as conn:
        conn.execute(
            "UPDATE documents SET local_path=?, downloaded_at=datetime('now') WHERE id=?",
            (local_path, doc_id))
