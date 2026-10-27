"""Gradio demo: python app.py --index data/idx_eg2 --videos data/davis_bench/videos
Image query (image/object) and text query (sentence, EN/VI, ordinal words) -> video + timestamp + segment."""
import argparse, os, time, cv2, gradio as gr
from vsearch.core import Searcher
ap = argparse.ArgumentParser(); ap.add_argument("--index", required=True); ap.add_argument("--videos", required=True); ap.add_argument("--share", action="store_true")
ap.add_argument("--hnsw-min", type=int, default=None, help="use FAISS HNSW for indexes with >= N vectors (off by default)")
ap.add_argument("--query-cache", type=int, default=0, help="LRU size for repeated-query embeddings (0 = off)")
ap.add_argument("--text-min-score", type=float, default=None, help="text search returns nothing if the best segment score is below this (EG2 calibrated: see README); default off")
ap.add_argument("--port", type=int, default=None); a = ap.parse_args()
S = Searcher(a.index, hnsw_min=a.hnsw_min, query_cache=a.query_cache)
VIDEOS = sorted({m["video"] for m in S.meta})
def frame_at(video, t, box):
    cap = cv2.VideoCapture(os.path.join(a.videos, video)); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read(); cap.release()
    if not ok: return None
    if box: cv2.rectangle(f, tuple(box[:2]), tuple(box[2:]), (0, 255, 0), 3)
    return cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
def show(segs):
    gal = [(frame_at(s["video"], s["peak_t"], s.get("box")), f"{s['video']} @ {s['peak_t']:.1f}s ({s['score']:.2f})") for s in segs]
    rows = [[s["video"], round(s["start"], 2), round(s["end"], 2), round(s["peak_t"], 2), round(s["score"], 3)] for s in segs]
    return gal, rows
def run(img, mode, k):
    if img is None: return [], [], ""
    t = time.time(); segs = S.search(img.convert("RGB"), mode, int(k)); return (*show(segs), f"{(time.time()-t)*1000:.0f} ms")
def run_text(q, video, method, k, thr):
    if not q or not q.strip(): return [], [], ""
    t = time.time(); segs = S.search_text(q, int(k), method=method, video=None if video == "(tất cả)" else video, min_score=thr if thr and thr > 0 else None)
    ms = f"{(time.time()-t)*1000:.0f} ms"
    return (*show(segs), ms if segs else f"Không tìm thấy (điểm cao nhất < ngưỡng {thr}) · {ms}")
with gr.Blocks(title="Đề 12 – Tìm kiếm ảnh/đối tượng/câu mô tả trong video") as demo:
    gr.Markdown("## Tìm trong video → video nguồn + thời điểm + đoạn\nTìm bằng ảnh (hoặc ảnh crop đối tượng), hoặc bằng câu mô tả tiếng Việt/Anh, "
                "ví dụ *con chó trắng đánh hơi*, *lần cuối cùng con chó xuất hiện*.")
    with gr.Row():
        with gr.Column():
            img = gr.Image(type="pil", label="Ảnh truy vấn")
            mode = gr.Radio(["frame", "region", "both"], value="frame" if "region" not in S.idx else "both", label="Chỉ mục"); btn = gr.Button("Tìm bằng ảnh")
        with gr.Column():
            txt = gr.Textbox(label="Câu truy vấn (tiếng Việt / English)", placeholder="khoảnh khắc ... đầu tiên")
            vid = gr.Dropdown(["(tất cả)"] + VIDEOS, value="(tất cả)", label="Giới hạn trong video")
            meth = gr.Radio(["window", "frame"], value="window", label="Gộp thời gian")
            thr = gr.Number(value=a.text_min_score or 0, label="Ngưỡng 'không tìm thấy' (0 = tắt)"); btn_t = gr.Button("Tìm bằng chữ")
    k = gr.Slider(1, 20, 5, step=1, label="Top-K"); lat = gr.Textbox(label="Độ trễ", interactive=False)
    gal = gr.Gallery(label="Kết quả", columns=5); tab = gr.Dataframe(headers=["video", "start(s)", "end(s)", "peak(s)", "score"])
    btn.click(run, [img, mode, k], [gal, tab, lat]); btn_t.click(run_text, [txt, vid, meth, k, thr], [gal, tab, lat]); txt.submit(run_text, [txt, vid, meth, k, thr], [gal, tab, lat])
demo.launch(share=a.share, server_port=a.port)
