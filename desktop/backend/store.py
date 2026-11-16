import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DEFAULTS = {"fps": 1.0, "batch_size": 2, "model_path": "", "vision_tokens": 140, "paused": False, "sampling": "uniform", "prefetch": True}


class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        for name in ("thumbnails", "previews", "models", "exports", "details", "sampling"):
            (root / name).mkdir(exist_ok=True)
        self.path = root / "library.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS folders(path TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS videos(
                    id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
                    duration REAL NOT NULL DEFAULT 0, width INTEGER NOT NULL DEFAULT 0,
                    height INTEGER NOT NULL DEFAULT 0, frames INTEGER NOT NULL DEFAULT 0,
                    total INTEGER NOT NULL DEFAULT 0, next_t REAL NOT NULL DEFAULT 0,
                    error TEXT NOT NULL DEFAULT '', added REAL NOT NULL, signature TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS frames(
                    id INTEGER PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                    t REAL NOT NULL, embedding BLOB NOT NULL, thumb TEXT NOT NULL,
                    UNIQUE(video_id,t)
                );
                CREATE INDEX IF NOT EXISTS frames_video ON frames(video_id,t);
                CREATE TABLE IF NOT EXISTS moments(
                    id TEXT PRIMARY KEY, video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                    start REAL NOT NULL, end REAL NOT NULL, peak REAL NOT NULL,
                    label TEXT NOT NULL, created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS history(query TEXT PRIMARY KEY, used REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS index_metrics(
                    video_id TEXT PRIMARY KEY REFERENCES videos(id) ON DELETE CASCADE,
                    frames INTEGER NOT NULL DEFAULT 0,
                    wall_seconds REAL NOT NULL DEFAULT 0,
                    decode_seconds REAL NOT NULL DEFAULT 0,
                    encode_seconds REAL NOT NULL DEFAULT 0,
                    write_seconds REAL NOT NULL DEFAULT 0,
                    device TEXT NOT NULL,
                    updated REAL NOT NULL
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(frames)")}
            for name in ("shot_start", "shot_end"):
                if name not in columns:
                    db.execute(f"ALTER TABLE frames ADD COLUMN {name} REAL")
            for key, value in DEFAULTS.items():
                db.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (key, json.dumps(value)))
            db.execute("UPDATE videos SET status='queued' WHERE status='indexing'")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def settings(self):
        with self.connect() as db:
            return {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT * FROM settings")}

    def update_settings(self, values):
        with self.connect() as db:
            for key, value in values.items():
                db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, json.dumps(value)))

    def videos(self):
        with self.connect() as db:
            rows = db.execute("""SELECT v.*,
                (SELECT id FROM frames f WHERE f.video_id=v.id ORDER BY t LIMIT 1) AS first_frame_id,
                m.frames AS measured_frames,m.wall_seconds AS index_seconds,
                m.decode_seconds,m.encode_seconds,m.write_seconds,m.device AS index_device
                FROM videos v LEFT JOIN index_metrics m ON m.video_id=v.id ORDER BY added DESC""")
            return [dict(row) for row in rows]

    def video(self, video_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()
            if row is None:
                raise KeyError("Video không có trong thư viện")
            return dict(row)
