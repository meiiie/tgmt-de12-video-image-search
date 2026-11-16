"""Create a local, read-only review of every test query; no media goes into Git."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import sqlite3

from retrieval_quality_metrics import peak_matches, temporal_iou


PAGE = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FrameAtlas · Kiểm tra bỏ sót & nhận nhầm</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f6f5f0;color:#202922;font:16px/1.5 system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:32px}h1{font-size:34px;line-height:1.2;margin:8px 0 16px}h2{font-size:20px}p{max-width:950px}.eyebrow{color:#386048;letter-spacing:.1em;font-size:12px;font-weight:700}label{display:inline-flex;flex-direction:column;gap:5px;margin:0 18px 14px 0}select{padding:10px;font:inherit;border:1px solid #a7b5a9;border-radius:7px;background:white}label.check{flex-direction:row;align-items:center}input{width:18px;height:18px}.controls,.summary{background:#fff;border:1px solid #d4dbd4;border-radius:12px;padding:20px;margin:20px 0}.summary{font-size:18px}.cases{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,530px),1fr));gap:20px}.case{background:#fff;border:1px solid #d4dbd4;border-radius:12px;padding:18px;overflow:hidden}.case h2{overflow-wrap:anywhere;margin:4px 0 12px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}figure{margin:0}img{width:100%;height:180px;object-fit:contain;background:#eceee8;border-radius:6px}figcaption,.detail{font-size:13px;color:#4d5c50}.bad{color:#a12a26}.good{color:#1d673c}button{font:inherit;padding:10px 18px;background:#204c35;color:white;border:0;border-radius:8px;margin:20px 0;cursor:pointer}a{color:#245d41}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;text-align:left;border-bottom:1px solid #ddd}.table-wrap{overflow-x:auto}#status{min-height:24px}.note{border-left:3px solid #b87728;padding-left:14px}details{margin-top:10px}@media(max-width:600px){main{padding:16px}h1{font-size:27px}img{height:140px}}
</style><main>
<div class="eyebrow">FRAMEATLAS / ĐO CHẤT LƯỢNG / 01.11.2026</div>
<h1>Tìm đúng cảnh, biết khi nào tìm sai.</h1>
<p>Thử nghiệm có nhãn từ DAVIS: 16 cảnh nguồn ghép thành 4 video, 12 cảnh khác chỉ dùng làm truy vấn vắng. Ảnh truy vấn không nằm trong video lập chỉ mục. Không phải độ chính xác chung của sản phẩm hay phép nhận dạng danh tính.</p>
<p class="note">Ảnh cùng nguồn vẫn gần nhau về nội dung. Mỗi đối tượng có 3 truy vấn tương quan. Ngưỡng chọn trên nhóm hiệu chỉnh; các kết quả dưới đây là nhóm kiểm tra. Cosine không phải xác suất đúng.</p>
<div class="controls"><label>Cấu hình<select id="config"></select></label><label>Ý định<select id="kind"><option value="object">Tìm đối tượng trong crop</option><option value="scene">Tìm cảnh của screenshot</option></select></label>
<label>Hiển thị<select id="filter"><option value="all">Tất cả truy vấn kiểm tra</option><option value="miss">Bỏ sót trong top 5</option><option value="false">Trả kết quả cho đối tượng vắng</option><option value="wrong">Kết quả đầu tiên sai</option></select></label>
<label class="check"><input id="threshold" type="checkbox">Áp dụng ngưỡng đã chọn trên nhóm hiệu chỉnh</label></div>
<div id="summary" class="summary" aria-live="polite"></div><div class="table-wrap"><table id="comparison"></table></div>
<p id="status" role="status">Đang tải kết quả…</p><div id="cases" class="cases"></div><button id="more" hidden>Xem thêm 12 truy vấn</button>
<p>Media chỉ dùng nghiên cứu local. Nguồn và điều khoản: <a href="https://davischallenge.org/davis2017/code.html">DAVIS 2017</a>; bản lưu README/SOURCES nằm trong thư mục provenance của bộ dữ liệu. Tìm bằng ngôn ngữ tự nhiên vẫn được giữ trong ứng dụng.</p>
</main><script>
const $=id=>document.getElementById(id);let data,shown=12;
const peakOK=(h,q)=>q.gt.some(g=>h.video===g.video&&g.start<=h.peak_t&&h.peak_t<g.end);
const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e};
function thumb(src,label){const f=make('figure');if(src){const img=make('img');img.src=src;img.alt=label;img.loading='lazy';f.append(img)}f.append(make('figcaption',label));return f}
function render(){const c=data.configurations.find(c=>c.id===$('config').value),kind=$('kind').value,on=$('threshold').checked;
const s=c.summary[kind][on?'test_calibrated':'test_raw'],tau=on?c.summary[kind].dev_calibrated.threshold:-1;
$('summary').textContent=`Đúng top 1: ${s.correct_top1}/${s.positive_queries} · Tìm thấy trong top 5: ${s.correct_top5}/${s.positive_queries} · Trả kết quả cho truy vấn vắng: ${s.false_accepted_absent}/${s.absent_queries} · Ngưỡng: ${on?tau.toFixed(4):'chưa áp dụng'}`;
const rows=c.queries.filter(q=>q.kind===kind).map(q=>({...q,accepted:q.hits.filter(h=>h.score>=tau)})).filter(q=>{
const filter=$('filter').value;return filter==='all'||filter==='miss'&&q.present&&!q.accepted.slice(0,5).some(h=>peakOK(h,q))||filter==='false'&&!q.present&&q.accepted.length||filter==='wrong'&&q.present&&q.accepted.length&&!peakOK(q.accepted[0],q)});
$('status').textContent=`${rows.length} truy vấn phù hợp bộ lọc · ${s.positive_targets} đối tượng/cảnh có mặt và ${s.absent_targets} đối tượng/cảnh vắng; mỗi mục có 3 ảnh truy vấn.`;
$('cases').replaceChildren();for(const q of rows.slice(0,shown)){const card=make('article',undefined,'case');const h=q.accepted[0];const correct=!!h&&peakOK(h,q);
card.append(make('div',q.present?'Có mặt trong thư viện':'Vắng trong thư viện','eyebrow'),make('h2',q.id));
const pair=make('div',undefined,'pair');pair.append(thumb('queries/'+q.image_name,'Ảnh truy vấn'),thumb(h?.thumb,h?`Ứng viên #1 · ${h.video} · ${h.peak_t.toFixed(2)} s`:'Không trả kết quả'));card.append(pair);
card.append(make('p',!h?'Đã từ chối truy vấn':correct?'Đúng video và mốc có nhãn':q.present?'Sai mốc hoặc sai video':'Có kết quả dù mục tiêu vắng',correct?'good':h?'bad':''));
card.append(make('p',h?`Cosine ${h.score.toFixed(4)} · đoạn ${h.start.toFixed(2)}–${h.end.toFixed(2)} s`:'', 'detail'));
if(q.present){card.append(make('p',q.sampled?'Chỉ mục có khung nằm trong khoảng nhãn.':'Chỉ mục không có khung nào nằm trong khoảng nhãn.','detail'));const details=make('details');details.append(make('summary','Xem khoảng thời gian đúng'));details.append(make('p',q.gt.map(g=>`${g.video}: ${g.start.toFixed(3)}–${g.end.toFixed(3)} s`).join('; '),'detail'));if(q.truth_thumb)details.append(thumb(q.truth_thumb,'Một khung trong khoảng nhãn'));card.append(details)}$('cases').append(card)}
$('more').hidden=shown>=rows.length;
const table=$('comparison');table.replaceChildren();const head=make('tr');for(const x of ['Cấu hình','Vector','Đúng top 1','Trúng top 5','Truy vấn vắng có kết quả'])head.append(make('th',x));table.append(head);
for(const cfg of data.configurations){const m=cfg.summary[kind][on?'test_calibrated':'test_raw'],tr=make('tr');for(const x of [cfg.id,cfg.indexed_vectors,`${m.correct_top1}/${m.positive_queries}`,`${m.correct_top5}/${m.positive_queries}`,`${m.false_accepted_absent}/${m.absent_queries}`])tr.append(make('td',String(x)));table.append(tr)}}
for(const id of ['config','kind','filter','threshold'])$(id).addEventListener('change',()=>{shown=12;render()});$('more').onclick=()=>{shown+=12;render()};
fetch('review.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{data=d;for(const c of d.configurations){const o=make('option',c.id);o.value=c.id;$('config').append(o)}$('config').value='frame_1fps_pad15';render()}).catch(e=>{$('status').textContent='Không tải được báo cáo: '+e.message});
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    manifest = json.loads((args.dataset / "manifest.json").read_text(encoding="utf-8"))
    queries = {q["id"]: q for q in manifest["queries"]}
    args.output.mkdir(parents=True, exist_ok=True)
    for sub in ("queries", "frames"):
        (args.output / sub).mkdir(exist_ok=True)
    library = args.report.parent / "library"
    db = sqlite3.connect((library / "library.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    try:
        frames = db.execute("SELECT v.name,f.t,f.thumb FROM frames f JOIN videos v ON v.id=f.video_id").fetchall()
    finally:
        db.close()
    frame_assets = {}
    for video, timestamp, thumb in frames:
        name = f"{Path(video).stem}-{round(timestamp * 1000)}.jpg"
        shutil.copyfile(library / "thumbnails" / thumb, args.output / "frames" / name)
        frame_assets[(video, timestamp)] = "frames/" + name
    records = []
    for config in report["configurations"]:
        for q in config["queries"]:
            threshold = config["summary"][q["kind"]]["dev_calibrated"]["threshold"]
            h = q["hits"][0] if q["hits"] else None
            records.append({"config": config["id"], "query": q["id"], "split": q["split"], "kind": q["kind"],
                "present": q["present"], "target": q["target"], "sampled": q["sampled"], "threshold_dev": threshold,
                "top1_score": h["score"] if h else None, "top1_video": h["video"] if h else None,
                "top1_peak": h["peak_t"] if h else None, "correct_top1": bool(h) and any(peak_matches(h, g) for g in q["gt"]),
                "correct_top5": any(peak_matches(h, g) for h in q["hits"][:5] for g in q["gt"]),
                "best_iou_top1": max((temporal_iou(h, g) for g in q["gt"]), default=0) if h else 0,
                "best_iou_top5": max((temporal_iou(h, g) for h in q["hits"][:5] for g in q["gt"]), default=0),
                "accepted_at_dev_threshold": bool(h) and h["score"] >= threshold})
            if q["split"] != "test":
                continue
            source = args.dataset / queries[q["id"]]["image"]
            q["image_name"] = source.name
            shutil.copyfile(source, args.output / "queries" / source.name)
            for hit in q["hits"]:
                hit["thumb"] = frame_assets[(hit["video"], hit["peak_t"])]
            q["truth_thumb"] = next((asset for (video, t), asset in frame_assets.items()
                if any(peak_matches({"video": video, "peak_t": t}, g) for g in q["gt"])), None)
        config["queries"] = [q for q in config["queries"] if q["split"] == "test"]
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (args.output / "review.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    (args.output / "index.html").write_text(PAGE, encoding="utf-8")
    print(json.dumps({"cases_in_csv": len(records), "review": str(args.output), "csv": str(args.csv)}))


if __name__ == "__main__":
    main()
