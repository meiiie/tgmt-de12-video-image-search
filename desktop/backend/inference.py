import hashlib
import json
import threading
from collections import OrderedDict
from pathlib import Path

import numpy as np

MODEL_ID = "google/embeddinggemma-2"
REVISION = "f9972ac22e696a105c482202646979e33e4b5a1e"


class Encoder:
    def __init__(self, root: Path, model_path="", vision_tokens=140):
        self.root = root
        self.model_path = model_path
        self.vision_tokens = vision_tokens
        self.model = None
        self.lock = threading.RLock()
        self.state = "not_loaded"
        self.error = ""
        self.device = "cpu"
        self.cache = OrderedDict()

    @property
    def signature(self):
        stamp = "official"
        if self.model_path:
            folder = Path(self.model_path)
            digest = hashlib.sha256()
            for path in sorted(folder.glob("*.safetensors")):
                stat = path.stat()
                digest.update(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode())
            config = folder / "config.json"
            if config.is_file():
                digest.update(config.read_bytes())
            stamp = digest.hexdigest()[:20]
        return f"{MODEL_ID}@{REVISION}:768:aspect:tokens{self.vision_tokens}:fp32-bf16:v3:{self.model_path}:{stamp}"

    def ensure(self):
        with self.lock:
            if self.model is not None:
                return
            try:
                self.state, self.error = "loading", ""
                import torch
                from sentence_transformers import SentenceTransformer
                from huggingface_hub import snapshot_download
                torch.set_num_threads(min(8, max(1, torch.get_num_threads())))
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                location = self.model_path
                if not location:
                    location = self.root / "models" / "embeddinggemma-2"
                    marker = location / ".frameatlas-revision"
                    if not marker.exists() or marker.read_text().strip() != REVISION:
                        self.state = "downloading"
                        snapshot_download(MODEL_ID, revision=REVISION, local_dir=location, ignore_patterns=["*.md", ".gitattributes"])
                        marker.write_text(REVISION)
                self.state = "loading"
                config = json.loads((Path(location) / "config.json").read_text(encoding="utf-8"))
                if config.get("model_type") != "embedding_gemma2":
                    raise ValueError("Thư mục đã chọn không phải model EmbeddingGemma 2")
                self.model = SentenceTransformer(
                    str(location), device=self.device,
                    config_kwargs={"audio_config": None},
                    model_kwargs={"dtype": torch.bfloat16 if self.device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32},
                )
                self.state = "ready"
            except Exception as error:
                self.state, self.error = "error", str(error)
                raise

    def images(self, images):
        with self.lock:
            self.ensure()
            vectors = np.asarray(self.model.encode(
                [{"image": image.convert("RGB")} for image in images],
                batch_size=len(images), normalize_embeddings=True, show_progress_bar=False,
                processing_kwargs={"image": {"max_soft_tokens": self.vision_tokens}},
            ), dtype=np.float32)
            if vectors.shape != (len(images), 768) or not np.isfinite(vectors).all():
                raise ValueError("Model phải trả về vector EG2 hữu hạn, 768 chiều. Hãy dùng FP32 hoặc BF16.")
            return vectors

    def query(self, text=None, image=None):
        key = "t:" + text if text is not None else "i:" + hashlib.sha256(image.convert("RGB").tobytes() + str(image.size).encode()).hexdigest()
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            self.ensure()
            if text is not None:
                vector = np.asarray(self.model.encode(
                    [text], prompt_name="SearchQuery", normalize_embeddings=True, show_progress_bar=False,
                ), dtype=np.float32)[0]
            else:
                vector = self.images([image])[0]
            if not np.isfinite(vector).all():
                raise ValueError("Model trả về vector không hữu hạn")
            self.cache[key] = vector
            if len(self.cache) > 64:
                self.cache.popitem(last=False)
            return vector
