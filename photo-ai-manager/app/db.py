"""SQLite 数据层：照片、标签、训练样本（学习记忆）、纠正历史。"""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager

DATA_DIR = os.environ.get(
    "PHOTO_DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
)

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    phash TEXT NOT NULL,
    dhash TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    taken_at TEXT,
    imported_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_photos_sha ON photos(sha256);

CREATE TABLE IF NOT EXISTS labels (
    photo_id INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,          -- person / scene / category
    label TEXT NOT NULL,
    source TEXT NOT NULL,             -- ai / learned / user
    confidence REAL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (photo_id, dimension)
);

CREATE TABLE IF NOT EXISTS training_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dimension TEXT NOT NULL,
    label TEXT NOT NULL,
    features TEXT NOT NULL,           -- JSON 数组（特征向量）
    photo_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_train_dim ON training_examples(dimension);

CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    old_label TEXT,
    new_label TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def db_path() -> str:
    return os.path.join(DATA_DIR, "app.db")


def photos_dir() -> str:
    return os.path.join(DATA_DIR, "photos")


def thumbs_dir() -> str:
    return os.path.join(DATA_DIR, "thumbs")


def init(data_dir: str | None = None) -> None:
    global DATA_DIR
    if data_dir:
        DATA_DIR = data_dir
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(photos_dir(), exist_ok=True)
    os.makedirs(thumbs_dir(), exist_ok=True)
    # 数据目录切换后（例如测试）丢弃线程内的旧连接
    if getattr(_local, "conn", None) is not None:
        _local.conn.close()
        _local.conn = None
    with connect() as conn:
        conn.executescript(SCHEMA)


def connect() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(db_path())
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return conn


@contextmanager
def tx():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ---------- photos ----------

def add_photo(filename, path, sha256, phash, dhash, width, height, taken_at) -> int:
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO photos (filename, path, sha256, phash, dhash, width, height, taken_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (filename, path, sha256, phash, dhash, width, height, taken_at),
        )
        return cur.lastrowid


def get_photo(photo_id: int):
    return connect().execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()


def find_by_sha(sha256: str):
    return connect().execute("SELECT * FROM photos WHERE sha256=?", (sha256,)).fetchone()


def all_photos():
    return connect().execute("SELECT * FROM photos ORDER BY id DESC").fetchall()


def delete_photo(photo_id: int) -> None:
    with tx() as conn:
        conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))


# ---------- labels ----------

def set_label(photo_id, dimension, label, source, confidence=0.0) -> None:
    with tx() as conn:
        conn.execute(
            "INSERT INTO labels (photo_id, dimension, label, source, confidence, updated_at)"
            " VALUES (?,?,?,?,?,datetime('now'))"
            " ON CONFLICT(photo_id, dimension) DO UPDATE SET"
            " label=excluded.label, source=excluded.source,"
            " confidence=excluded.confidence, updated_at=excluded.updated_at",
            (photo_id, dimension, label, source, confidence),
        )


def get_labels(photo_id: int):
    return connect().execute(
        "SELECT * FROM labels WHERE photo_id=?", (photo_id,)
    ).fetchall()


def known_labels(dimension: str | None = None) -> dict:
    """返回每个维度已出现过的标签列表（用户教过的优先）。"""
    q = (
        "SELECT dimension, label, MAX(source='user') AS taught, COUNT(*) AS n"
        " FROM labels GROUP BY dimension, label"
        " ORDER BY taught DESC, n DESC"
    )
    out: dict[str, list[str]] = {}
    for row in connect().execute(q):
        out.setdefault(row["dimension"], []).append(row["label"])
    if dimension:
        return {dimension: out.get(dimension, [])}
    return out


# ---------- learning ----------

def add_training_example(dimension, label, vector, photo_id=None) -> int:
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO training_examples (dimension, label, features, photo_id)"
            " VALUES (?,?,?,?)",
            (dimension, label, json.dumps(vector), photo_id),
        )
        return cur.lastrowid


def training_examples(dimension: str):
    rows = connect().execute(
        "SELECT label, features FROM training_examples WHERE dimension=?", (dimension,)
    ).fetchall()
    return [(r["label"], json.loads(r["features"])) for r in rows]


def add_correction(photo_id, dimension, old_label, new_label) -> None:
    with tx() as conn:
        conn.execute(
            "INSERT INTO corrections (photo_id, dimension, old_label, new_label)"
            " VALUES (?,?,?,?)",
            (photo_id, dimension, old_label, new_label),
        )


def stats() -> dict:
    conn = connect()
    n_photos = conn.execute("SELECT COUNT(*) c FROM photos").fetchone()["c"]
    n_train = conn.execute("SELECT COUNT(*) c FROM training_examples").fetchone()["c"]
    n_corr = conn.execute("SELECT COUNT(*) c FROM corrections").fetchone()["c"]
    by_dim = {
        r["dimension"]: r["c"]
        for r in conn.execute(
            "SELECT dimension, COUNT(*) c FROM training_examples GROUP BY dimension"
        )
    }
    return {
        "photos": n_photos,
        "training_examples": n_train,
        "corrections": n_corr,
        "learned_by_dimension": by_dim,
    }
