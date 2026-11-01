import argparse
import base64
from contextlib import asynccontextmanager
import hmac
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import socket
import threading
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .library import Library
from .media import export_clip, preview_path


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ImportBody(Body):
    paths: list[str] = Field(min_length=1, max_length=500)


class SettingsBody(Body):
    fps: float | None = Field(default=None, ge=0.1, le=4)
    batch_size: int | None = Field(default=None, ge=1, le=16)
    model_path: str | None = Field(default=None, max_length=4096)
    paused: bool | None = None
    vision_tokens: Literal[70, 140, 280] | None = None


class SearchBody(Body):
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    image: str | None = Field(default=None, max_length=12_000_000)
    video_id: str | None = None
    limit: int = Field(default=24, ge=1, le=100)
    min_score: float = Field(default=-1, ge=-1, le=1)
    occurrence: Literal[1, 2, 3, -1] | None = None

    @model_validator(mode="after")
    def query_required(self):
        if bool(self.text and self.text.strip()) == bool(self.image):
            raise ValueError("Cung cấp một truy vấn văn bản hoặc ảnh")
        if self.occurrence and not self.video_id:
            raise ValueError("Chọn một video khi tìm lần xuất hiện theo thứ tự")
        return self


class MomentBody(Body):
    video_id: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    peak: float = Field(ge=0)
    label: str = Field(min_length=1, max_length=300)


class ExportBody(Body):
    video_id: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    path: str = Field(min_length=1, max_length=4096)


ORIGINS = ["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost", "http://127.0.0.1:1420", "http://localhost:1420"]


def create_app(library: Library, token: str):
    @asynccontextmanager
    async def lifespan(app):
        yield
        library.close()

    app = FastAPI(title="FrameAtlas local worker", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "Range"])

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in ORIGINS:
            return JSONResponse({"detail": "Origin not allowed"}, 403)
        if request.method == "OPTIONS":
            return await call_next(request)
        supplied = request.headers.get("authorization", "").removeprefix("Bearer ")
        if request.url.path.startswith(("/media/", "/thumbnails/")):
            supplied = supplied or request.query_params.get("token", "")
        if not hmac.compare_digest(supplied, token):
            return JSONResponse({"detail": "Local authorization required"}, 401)
        if int(request.headers.get("content-length", "0")) > 13_000_000:
            return JSONResponse({"detail": "Request too large"}, 413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(KeyError)
    async def missing(request, error):
        return JSONResponse({"detail": str(error).strip("'")}, 404)

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse({"detail": str(error)}, 400)

    @app.exception_handler(OSError)
    async def io_error(request, error):
        return JSONResponse({"detail": str(error)}, 400)

    @app.exception_handler(Exception)
    async def unexpected(request, error):
        logging.exception("Local worker operation failed", exc_info=error)
        return JSONResponse({"detail": f"Không hoàn tất được thao tác: {error}"}, 500)

    @app.get("/health")
    def health():
        return {"ok": True, "version": "0.1.0"}

    @app.get("/library")
    def status():
        return library.status()

    @app.post("/import")
    def import_files(body: ImportBody):
        return library.import_paths(body.paths)

    @app.post("/rescan")
    def rescan():
        return library.rescan()

    @app.delete("/folders")
    def forget_folder(body: ImportBody):
        with library.store.connect() as db:
            db.executemany("DELETE FROM folders WHERE path=?", [(p,) for p in body.paths])
        return {"ok": True}

    @app.patch("/settings")
    def settings(body: SettingsBody):
        values = body.model_dump(exclude_none=True)
        path = values.get("model_path")
        if path and not (Path(path).is_dir() and (Path(path) / "modules.json").is_file()):
            raise ValueError("Chọn thư mục EG2 có modules.json")
        library.settings(values)
        return {"ok": True}

    @app.post("/model/prepare")
    def prepare():
        library.prepare()
        return {"ok": True}

    @app.post("/videos/{video_id}/{action}")
    def job(video_id: str, action: Literal["cancel", "retry", "remove"]):
        library.job(video_id, action)
        return {"ok": True}

    @app.get("/videos/{video_id}")
    def source(video_id: str):
        return library.store.video(video_id)

    @app.post("/search")
    def search(body: SearchBody):
        image = None
        if body.image:
            try:
                payload = base64.b64decode(body.image, validate=True)
                image = Image.open(BytesIO(payload))
                if image.width * image.height > 24_000_000:
                    raise ValueError("Ảnh tối đa 24 megapixel")
                image.load()
                image = image.convert("RGB")
            except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
                raise ValueError("Không đọc được ảnh truy vấn") from error
        return library.search(text=body.text.strip() if body.text else None, image=image, video_id=body.video_id, limit=body.limit, min_score=body.min_score, occurrence=body.occurrence)

    @app.get("/thumbnails/{frame_id}")
    def thumbnail(frame_id: int):
        with library.store.connect() as db:
            row = db.execute("SELECT thumb FROM frames WHERE id=?", (frame_id,)).fetchone()
        if row is None:
            raise KeyError("Khung hình không còn trong chỉ mục")
        return FileResponse(library.root / "thumbnails" / row[0], media_type="image/jpeg")

    @app.get("/media/{video_id}")
    def media(video_id: str):
        path = preview_path(library.store.video(video_id), library.root)
        return FileResponse(path, media_type="video/mp4")

    @app.get("/moments")
    def moments():
        return library.moments()

    @app.post("/moments")
    def save(body: MomentBody):
        identity = library.save_moment(**body.model_dump())
        return {"id": identity}

    @app.delete("/moments/{moment_id}")
    def delete(moment_id: str):
        with library.store.connect() as db:
            db.execute("DELETE FROM moments WHERE id=?", (moment_id,))
        return {"ok": True}

    @app.post("/export")
    def export(body: ExportBody):
        path = export_clip(library.store.video(body.video_id), body.start, body.end, Path(body.path))
        return {"path": path}

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--parent", type=int)
    args = parser.parse_args()
    token = os.environ.get("FRAMEATLAS_TOKEN", "")
    if len(token) < 32:
        raise SystemExit("FRAMEATLAS_TOKEN must have at least 32 characters")
    if args.parent:
        def monitor():
            import psutil
            try:
                parent = psutil.Process(args.parent)
                parent.wait()
            finally:
                os._exit(0)
        threading.Thread(target=monitor, daemon=True).start()
    import uvicorn
    library = Library(args.data_dir)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", args.port))
    sock.listen(128)
    print(json.dumps({"port": sock.getsockname()[1]}), flush=True)
    uvicorn.Server(uvicorn.Config(create_app(library, token), log_level="warning", access_log=False)).run(sockets=[sock])


if __name__ == "__main__":
    main()
