"""Gradio demo: python app.py --index data/index_davis"""
import argparse, os, cv2, gradio as gr
from vsearch.core import Searcher
ap = argparse.ArgumentParser(); ap.add_argument("--index", required=True); ap.add_argument("--videos", required=True); ap.add_argument("--share", action="store_true"); a = ap.parse_args()
S = Searcher(a.index)
def frame_at(video, t, box):
    cap = cv2.VideoCapture(os.path.join(a.videos, video)); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read(); cap.release()
    if not ok: return None
    if box: cv2.rectangle(f, tuple(box[:2]), tuple(box[2:]), (0, 255, 0), 3)
    return cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
def run(img, mode, k):
    if img is None: return [], []
    segs = S.search(img.convert("RGB"), mode, int(k))
    gal = [(frame_at(s["video"], s["peak_t"], s["box"]), f"{s['video']} @ {s['peak_t']:.1f}s ({s['score']:.2f})") for s in segs]
    rows = [[s["video"], s["start"], s["end"], s["peak_t"], round(s["score"], 3)] for s in segs]
    return gal, rows
with gr.Blocks(title="Đề 12 – Tìm kiếm ảnh/đối tượng trong video") as demo:
    gr.Markdown("## Tìm kiếm ảnh / đối tượng trong video → video nguồn + thời điểm\nTải ảnh (hoặc ảnh crop đối tượng) lên.")
    with gr.Row():
        img = gr.Image(type="pil", label="Ảnh truy vấn"); 
        with gr.Column():
            mode = gr.Radio(["frame", "region", "both"], value="both", label="Chỉ mục"); k = gr.Slider(1, 20, 5, step=1, label="Top-K"); btn = gr.Button("Tìm")
    gal = gr.Gallery(label="Kết quả", columns=5); tab = gr.Dataframe(headers=["video", "start(s)", "end(s)", "peak(s)", "score"])
    btn.click(run, [img, mode, k], [gal, tab])
demo.launch(share=a.share)
