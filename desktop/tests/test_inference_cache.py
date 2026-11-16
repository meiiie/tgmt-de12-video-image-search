from concurrent.futures import ThreadPoolExecutor
import threading

import numpy as np
from PIL import Image
import pytest

from desktop.backend.inference import Encoder


def test_cached_query_can_finish_while_indexing_owns_model(tmp_path):
    encoder = Encoder(tmp_path)
    cached = np.array([1, 0, 0], dtype="float32")
    encoder.cache["t:known scene"] = cached
    finished = threading.Event()

    def search():
        value = encoder.query(text="known scene")
        finished.set()
        return value

    with ThreadPoolExecutor(max_workers=1) as pool:
        with encoder.lock:
            future = pool.submit(search)
            completed_during_inference = finished.wait(timeout=2)
        assert completed_during_inference
        np.testing.assert_array_equal(future.result(), cached)
    assert encoder.model is None


def test_embeddings_are_normalized_in_float32_after_model_output(tmp_path):
    class Model:
        def encode(self, inputs, **kwargs):
            vectors = np.zeros((len(inputs), 768), dtype="float32")
            vectors[:, :2] = [.6, .8]
            return vectors * 1.003

    encoder = Encoder(tmp_path)
    encoder.model = Model()
    image = Image.new("RGB", (4, 4), "red")
    vectors = encoder.images([image, image])
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-6)
    assert np.linalg.norm(encoder.query(text="red")) == pytest.approx(1, abs=1e-6)
