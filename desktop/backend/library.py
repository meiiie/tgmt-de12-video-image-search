import hashlib
import math
import os
from pathlib import Path
import threading
import time
import uuid

import cv2
import numpy as np
from PIL import Image

from .inference import Encoder
from .media import EXTENSIONS, fingerprint
from .store import Store


class Library:
    def __init__(self, root: Path, encoder=None, start_worker=True):
        self.store = Store(root)
        self.root = root
        settings = self.store.settings()
        self.encoder = encoder or Encoder(root, settings["model_path"], settings["vision_tokens"])
        signature = self.encoder.signature + f':fps={settings["fps"]}'
        with self.store.connect() as db:
            db.execute("DELETE FROM frames WHERE video_id IN (SELECT id FROM videos WHERE signature<>'' AND signature<>?)", (signature,))
            db.execute("UPDATE videos SET status='queued',frames=0,next_t=0,error='',signature='' WHERE signature<>'' AND signature<>?", (signature,))
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.revision = 0
        self.snapshot = None
        self.snapshot_revision = -1
        self.search_lock = threading.Lock()
        self.state_lock = threading.RLock()
        self.active = None
        self.thread = None
        self.prepare_lock = threading.Lock()
        if start_worker:
            self.thread = threading.Thread(target=self._worker, daemon=True)
            self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=5)

    def import_paths(self, paths):
        files, errors, added = set(), [], 0
        for raw in paths:
            path = Path(raw).expanduser().resolve()
            if path.is_dir():
                with self.store.connect() as db:
                    db.execute("INSERT OR IGNORE INTO folders VALUES(?)", (str(path),))
                for base, dirs, names in os.walk(path):
                    dirs[:] = [d for d in dirs if not d.startswith(".") and not Path(base, d).is_symlink()]
                    files.update(Path(base, name) for name in names if Path(name).suffix.lower() in EXTENSIONS and not Path(base, name).is_symlink())
            elif path.is_file() and path.suffix.lower() in EXTENSIONS:
                files.add(path)
            else:
                errors.append(f"Không phải video/thư mục hỗ trợ: {path}")
        for path in sorted(files):
            try:
                canonical = str(path.resolve())
                identity = hashlib.sha256(os.path.normcase(canonical).encode()).hexdigest()[:24]
                stamp = fingerprint(path)
                with self.store.connect() as db:
                    old = db.execute("SELECT * FROM videos WHERE id=?", (identity,)).fetchone()
                    if old and old["fingerprint"] == stamp:
                        continue
                    if old:
                        db.execute("DELETE FROM frames WHERE video_id=?", (identity,))
                        db.execute("UPDATE videos SET fingerprint=?,status='queued',frames=0,next_t=0,error='',signature='' WHERE id=?", (stamp, identity))
                    else:
                        db.execute("INSERT INTO videos(id,path,name,fingerprint,added) VALUES(?,?,?,?,?)", (identity, canonical, path.name, stamp, time.time()))
                    added += 1
                self.revision += 1
            except OSError as error:
                errors.append(f"{path.name}: {error}")
        self.wake.set()
        return {"added": added, "errors": errors, "discovered": len(files)}

    def rescan(self):
        with self.store.connect() as db:
            paths = [row[0] for row in db.execute("SELECT path FROM folders")]
            paths += [row[0] for row in db.execute("SELECT path FROM videos")]
        return self.import_paths(paths)

    def status(self):
        videos = self.store.videos()
        with self.store.connect() as db:
            saved = db.execute("SELECT COUNT(*) FROM moments").fetchone()[0]
            folders = [r[0] for r in db.execute("SELECT path FROM folders")]
            history = [r[0] for r in db.execute("SELECT query FROM history ORDER BY used DESC LIMIT 8")]
        return {
            "videos": videos, "settings": self.store.settings(), "folders": folders, "history": history,
            "model": {"state": self.encoder.state, "error": self.encoder.error, "device": self.encoder.device},
            "summary": {"videos": len(videos), "ready": sum(v["status"] == "ready" for v in videos), "frames": sum(v["frames"] for v in videos), "duration": sum(v["duration"] for v in videos), "saved": saved},
            "active": self.active, "data_dir": str(self.root),
        }

    def prepare(self):
        with self.state_lock:
            if not self.prepare_lock.acquire(blocking=False):
                return
            encoder = self.encoder
        def load():
            try:
                encoder.ensure()
            except Exception:
                pass
            finally:
                self.prepare_lock.release()
        threading.Thread(target=load, daemon=True).start()

    def job(self, video_id, action):
        with self.state_lock, self.store.connect() as db:
            self.store.video(video_id)
            if action == "remove":
                db.execute("DELETE FROM videos WHERE id=?", (video_id,))
            elif action == "cancel":
                db.execute("UPDATE videos SET status='cancelled' WHERE id=?", (video_id,))
            else:
                db.execute("UPDATE videos SET status='queued',error='' WHERE id=?", (video_id,))
        self.revision += 1
        self.wake.set()

    def settings(self, values):
        with self.search_lock, self.state_lock:
            self._settings(values)

    def _settings(self, values):
        old = self.store.settings()
        changed = any(key in values and values[key] != old[key] for key in ("fps", "model_path", "vision_tokens"))
        if changed and (self.active or self.encoder.state in {"loading", "downloading"} or self.prepare_lock.locked()):
            raise ValueError("Tạm dừng và đợi tác vụ hiện tại kết thúc trước khi đổi model/tần suất")
        self.store.update_settings(values)
        if changed:
            with self.store.connect() as db:
                db.execute("DELETE FROM frames")
                db.execute("UPDATE videos SET status='queued',frames=0,next_t=0,error='',signature=''")
            settings = self.store.settings()
            self.encoder = Encoder(self.root, settings["model_path"], settings["vision_tokens"])
            self.revision += 1
        self.wake.set()

    def _worker(self):
        while not self.stop.is_set():
            if not self.store.settings()["paused"]:
                with self.store.connect() as db:
                    row = db.execute("SELECT * FROM videos WHERE status='queued' ORDER BY added LIMIT 1").fetchone()
                if row:
                    self.index_video(dict(row))
                    continue
            self.wake.wait(1)
            self.wake.clear()

    def _current(self, video):
        if self.stop.is_set() or self.store.settings()["paused"]:
            return False
        try:
            current = self.store.video(video["id"])
            return current["status"] == "indexing" and current["fingerprint"] == video["fingerprint"]
        except KeyError:
            return False

    def index_video(self, video):
        identity = video["id"]
        with self.state_lock:
            try:
                video = self.store.video(identity)
            except KeyError:
                return
            if video["status"] != "queued" or self.store.settings()["paused"]:
                return
            self.active = identity
            with self.store.connect() as db:
                db.execute("UPDATE videos SET status='indexing',error='' WHERE id=?", (identity,))
        cap = None
        try:
            settings = self.store.settings()
            signature = self.encoder.signature + f':fps={settings["fps"]}'
            if fingerprint(Path(video["path"])) != video["fingerprint"]:
                self.import_paths([video["path"]])
                return
            with self.store.connect() as db:
                if video["signature"] and video["signature"] != signature:
                    db.execute("DELETE FROM frames WHERE video_id=?", (identity,))
                    db.execute("UPDATE videos SET next_t=0,frames=0 WHERE id=?", (identity,))
                    video["next_t"] = 0
                db.execute("UPDATE videos SET signature=? WHERE id=? AND status='indexing'", (signature, identity))
            self.encoder.ensure()
            cap = cv2.VideoCapture(video["path"])
            native_fps = cap.get(cv2.CAP_PROP_FPS)
            count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if not cap.isOpened() or not math.isfinite(native_fps) or native_fps <= 0 or count <= 0:
                raise ValueError("Không giải mã được video hoặc video không có khung hình")
            duration = count / native_fps
            step = max(1, round(native_fps / settings["fps"]))
            total = math.ceil(count / step)
            with self.store.connect() as db:
                db.execute("UPDATE videos SET duration=?,width=?,height=?,total=? WHERE id=?", (duration, int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), total, identity))
            i = int(round(video["next_t"] * native_fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            while i < count and self._current(video):
                batch, times = [], []
                for _ in range(settings["batch_size"]):
                    ok, frame = cap.read()
                    if not ok:
                        break
                    batch.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                    times.append(round(i / native_fps, 6))
                    for _ in range(step - 1):
                        cap.grab()
                    i += step
                    if i >= count:
                        break
                if not batch:
                    raise ValueError("Video bị ngắt hoặc lỗi giải mã giữa chừng")
                vectors = self.encoder.images(batch)
                if not self._current(video):
                    break
                records = []
                for image, t, vector in zip(batch, times, vectors):
                    name = f"{identity}-{round(t * 1000000)}.jpg"
                    image.thumbnail((384, 216))
                    image.save(self.root / "thumbnails" / name, quality=82)
                    records.append((identity, t, vector.astype("float32").tobytes(), name))
                with self.store.connect() as db:
                    current = db.execute("SELECT status,fingerprint FROM videos WHERE id=?", (identity,)).fetchone()
                    if not current or current["status"] != "indexing" or current["fingerprint"] != video["fingerprint"]:
                        break
                    db.executemany("INSERT OR REPLACE INTO frames(video_id,t,embedding,thumb) VALUES(?,?,?,?)", records)
                    db.execute("UPDATE videos SET next_t=?,frames=(SELECT COUNT(*) FROM frames WHERE video_id=?) WHERE id=?", (i / native_fps, identity, identity))
                self.revision += 1
                time.sleep(0.01)
            with self.store.connect() as db:
                db.execute("UPDATE videos SET status=CASE WHEN frames >= total AND total > 0 THEN 'ready' ELSE 'queued' END WHERE id=? AND status='indexing' AND fingerprint=?", (identity, video["fingerprint"]))
        except Exception as error:
            with self.store.connect() as db:
                db.execute("UPDATE videos SET status='error',error=? WHERE id=? AND status='indexing' AND fingerprint=?", (str(error)[-1500:], identity, video["fingerprint"]))
        finally:
            if cap is not None:
                cap.release()
            self.active = None

    def search(self, text=None, image=None, video_id=None, limit=24, min_score=-1, occurrence=None):
        from vsearch.text import text_search
        started = time.perf_counter()
        ordinal = occurrence
        with self.search_lock:
            if self.snapshot_revision != self.revision:
                revision = self.revision
                with self.store.connect() as db:
                    rows = db.execute("SELECT f.*,v.name,v.path,v.duration FROM frames f JOIN videos v ON v.id=f.video_id ORDER BY f.video_id,f.t").fetchall()
                self.snapshot = ([{key: r[key] for key in r.keys() if key != "embedding"} for r in rows], np.stack([np.frombuffer(r["embedding"], dtype="float32") for r in rows]) if rows else None)
                self.snapshot_revision = revision
            rows, matrix = self.snapshot
            if not rows:
                return {"results": [], "elapsed_ms": 0, "indexed_frames": 0}
            q = self.encoder.query(text=text, image=image)
            scores = matrix @ q
            meta = [{"video": r["video_id"], "t": r["t"], "kind": "frame"} for r in rows]
            fps = self.store.settings()["fps"]
            if video_id and not any(r["video_id"] == video_id for r in rows):
                return {"results": [], "elapsed_ms": 0, "indexed_frames": len(rows)}
            if ordinal and not video_id:
                best = text_search(meta, None, None, fps, scores=scores, k=1)
                video_id = best[0]["video"] if best else None
            segments = text_search(meta, None, None, fps, scores=scores, video=video_id, k=limit, ordinal=ordinal, ord_v2={"rho": 0.3, "gap": 1.0, "dup": None})
            results = []
            by_video = {}
            for row in rows:
                by_video.setdefault(row["video_id"], []).append(row)
            for segment in segments:
                if segment["score"] < min_score:
                    continue
                near = min(by_video[segment["video"]], key=lambda row: abs(row["t"] - segment["peak_t"]))
                results.append({"video_id": near["video_id"], "name": near["name"], "path": near["path"], "duration": near["duration"], "frame_id": near["id"], "start": max(0, segment["start"]), "end": min(near["duration"], segment["end"]), "peak": segment["peak_t"], "score": segment["score"]})
        if text:
            with self.store.connect() as db:
                db.execute("INSERT OR REPLACE INTO history VALUES(?,?)", (text, time.time()))
                db.execute("DELETE FROM history WHERE query NOT IN (SELECT query FROM history ORDER BY used DESC LIMIT 50)")
        return {"results": results, "elapsed_ms": round((time.perf_counter() - started) * 1000), "indexed_frames": len(rows)}

    def save_moment(self, video_id, start, end, peak, label):
        video = self.store.video(video_id)
        if start < 0 or end <= start or end > video["duration"] + 0.1 or not start <= peak <= end:
            raise ValueError("Khoảng thời gian lưu không hợp lệ")
        identity = uuid.uuid4().hex
        with self.store.connect() as db:
            db.execute("INSERT INTO moments VALUES(?,?,?,?,?,?,?)", (identity, video_id, start, end, peak, label, time.time()))
        return identity

    def moments(self):
        with self.store.connect() as db:
            moments = [dict(r) for r in db.execute("SELECT m.*,v.name,v.path,v.duration FROM moments m JOIN videos v ON v.id=m.video_id ORDER BY created DESC")]
            for moment in moments:
                frame = db.execute("SELECT id FROM frames WHERE video_id=? ORDER BY ABS(t-?) LIMIT 1", (moment["video_id"], moment["peak"])).fetchone()
                moment["frame_id"] = frame[0] if frame else None
            return moments
