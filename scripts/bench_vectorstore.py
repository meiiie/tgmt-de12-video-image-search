"""Benchmark vector stores for EG2 search (CPU). Usage: python bench_vectorstore.py out.json"""
import sys, time, json, os, gc, shutil, tempfile, hashlib
import numpy as np, faiss, psutil
faiss.omp_set_num_threads(1)  # single query latency, 1 thread
rng = np.random.default_rng(0)
def rss(): return psutil.Process().memory_info().rss / 2**20
def unit(x): return (x / np.linalg.norm(x, axis=1, keepdims=True)).astype("float32")
def synth(n, d, nc=1000):
    # clustered synthetic (Gaussian mixture), not real embeddings
    C = unit(rng.standard_normal((nc, d)).astype("float32"))
    out = np.empty((n, d), "float32")
    for s in range(0, n, 100000):
        e = min(n, s + 100000); a = rng.integers(0, nc, e - s)
        out[s:e] = unit(C[a] + 0.6 / np.sqrt(d) * rng.standard_normal((e - s, d)).astype("float32") * np.sqrt(d) / 1.0 * 0.05)
    return out
def queries(X, nq=200):
    i = rng.integers(0, len(X), nq)
    return unit(X[i] + 0.02 * rng.standard_normal(X[i].shape).astype("float32"))
def lat(fn, Q):
    t = []
    for q in Q:
        s = time.perf_counter(); fn(q[None]); t.append((time.perf_counter() - s) * 1e3)
    return float(np.percentile(t, 50)), float(np.percentile(t, 95))
def run(name, X, Q, chroma=True):
    n, d = X.shape; k = min(10, n); res = []
    gt = faiss.IndexFlatIP(d); gt.add(X); _, G = gt.search(Q, k)
    def rec(I): return float(np.mean([len(set(a) & set(b)) / k for a, b in zip(I, G)]))
    nl = max(1, int(4 * np.sqrt(n)))
    cfgs = [("FlatIP", lambda: faiss.IndexFlatIP(d), None)]
    hn = lambda: (lambda ix: (setattr(ix.hnsw, "efConstruction", 40), ix)[1])(faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT))
    cfgs.append(("HNSW32 ef64", hn, ("efSearch", 64)))
    if n >= 10000:
        cfgs.append((f"IVF{nl}-Flat np16", lambda: faiss.IndexIVFFlat(faiss.IndexFlatIP(d), d, nl, faiss.METRIC_INNER_PRODUCT), ("nprobe", 16)))
        cfgs.append((f"IVF{nl}-PQ{d//8}x8 np16", lambda: faiss.IndexIVFPQ(faiss.IndexFlatIP(d), d, nl, d // 8, 8, faiss.METRIC_INNER_PRODUCT), ("nprobe", 16)))
    for nm, mk, par in cfgs:
        gc.collect(); m0 = rss(); faiss.omp_set_num_threads(8); t0 = time.perf_counter()
        ix = mk()
        if not ix.is_trained: ix.train(X[rng.choice(n, min(n, 100000), replace=False)])
        ix.add(X); bt = time.perf_counter() - t0; faiss.omp_set_num_threads(1)
        if par:
            if par[0] == "efSearch": ix.hnsw.efSearch = par[1]
            else: ix.nprobe = par[1]
        _, I = ix.search(Q, k); p50, p95 = lat(lambda q: ix.search(q, k), Q[:100])
        res.append(dict(set=name, store="FAISS " + nm, n=n, d=d, build_s=round(bt, 2), mem_mb=round(rss() - m0, 1), p50_ms=round(p50, 3), p95_ms=round(p95, 3), recall10=round(rec(I), 3)))
        print(res[-1], flush=True); del ix
    if chroma and n <= 100000:
        import chromadb
        tmp = tempfile.mkdtemp(dir="/workspace"); gc.collect(); m0 = rss(); t0 = time.perf_counter()
        cl = chromadb.PersistentClient(path=tmp); c = cl.create_collection("eg2bench", metadata={"hnsw:space": "ip"})
        for s in range(0, n, 5000):
            c.add(ids=[str(i) for i in range(s, min(n, s + 5000))], embeddings=X[s:min(n, s + 5000)])
        bt = time.perf_counter() - t0
        I = [[int(x) for x in c.query(query_embeddings=q[None], n_results=k)["ids"][0]] for q in Q]
        p50, p95 = lat(lambda q: c.query(query_embeddings=q, n_results=k), Q[:100])
        res.append(dict(set=name, store="ChromaDB (HNSW, persistent)", n=n, d=d, build_s=round(bt, 2), mem_mb=round(rss() - m0, 1), p50_ms=round(p50, 3), p95_ms=round(p95, 3), recall10=round(rec(I), 3)))
        print(res[-1], flush=True); del c, cl; shutil.rmtree(tmp, ignore_errors=True)
    return res
out = []
ix = faiss.read_index("data/idx_eg2/frame.faiss")
base = faiss.downcast_index(ix.index) if hasattr(ix, "index") else ix
R = unit(base.reconstruct_n(0, base.ntotal)); print("real EG2 vectors", R.shape)
out += run("real EG2 box index (73)", R, queries(R))
out += run("real EG2 MRL-256", unit(R[:, :256]), unit(queries(R)[:, :256]))
for n in (100000, 1000000):
    for d in (768, 256):
        X = synth(n, d); out += run(f"synthetic clustered {n}", X, queries(X), chroma=(n <= 100000)); del X; gc.collect()
# query-embedding cache hit path: sha256 of image bytes -> dict lookup
img = os.urandom(150000); cache = {hashlib.sha256(img).hexdigest(): R[0]}
t = []
for _ in range(1000):
    s = time.perf_counter(); v = cache.get(hashlib.sha256(img).hexdigest()); t.append((time.perf_counter() - s) * 1e3)
out.append(dict(set="query cache", store="sha256(150KB)+dict", p50_ms=round(float(np.percentile(t, 50)), 4), p95_ms=round(float(np.percentile(t, 95)), 4)))
print(out[-1]); json.dump(out, open(sys.argv[1], "w"), indent=1)
