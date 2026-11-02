"""Render private real-video query evidence as a local static review page."""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3

HTML = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FrameAtlas · Kiểm thử video thực tế</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f5f0;color:#24362a;font:16px/1.5 system-ui}main{max-width:1280px;margin:auto;padding:32px}h1{font-size:34px;margin:8px 0}h2{font-size:20px}.eyebrow{letter-spacing:.1em;font-size:12px;font-weight:700}p{max-width:1050px}section{background:white;border:1px solid #d1dbd2;border-radius:12px;padding:20px;margin:20px 0}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #ddd}label{display:inline-flex;flex-direction:column;gap:5px;margin:8px 20px 8px 0}select{font:inherit;padding:10px;border-radius:8px;border:1px solid #a7b5a9;max-width:100%}figure{margin:0}img{width:100%;height:190px;object-fit:contain;background:#eef0e9;border-radius:7px}figcaption{font-size:13px}.query img{height:330px}.query{max-width:760px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}.good{color:#19613b}.note{border-left:3px solid #b77d36;padding-left:14px}.dim{font-size:13px;color:#59645b}a{color:#285d40}@media(max-width:650px){main{padding:16px}h1{font-size:27px}.query img{height:230px}}
</style><main><div class="eyebrow">FRAMEATLAS / VIDEO THỰC TẾ / 02.11.2026</div><h1>Ảnh này đưa ta về đoạn nào?</h1>
<p id="overview"></p><p class="note">Đo tìm lại mốc nguồn trong ±3 giây, không đo đủ mọi lần xuất hiện của nhân vật. Cảnh game và giao diện lặp lại; một mốc khác vẫn có thể giống ảnh. Các ảnh ngoài nguồn là phép thử từ chối, chưa phải nhãn “vắng” đầy đủ cho cả video.</p>
<section class="scroll"><table id="table"></table></section>
<section><label>Ảnh truy vấn<select id="query"></select></label><label>Cách tìm<select id="method"></select></label><p id="status" role="status"></p><figure class="query"><img id="reference" alt="Ảnh truy vấn thực sự gửi đi"><figcaption id="caption"></figcaption></figure></section>
<section><h2>Các khung được trả về</h2><p id="audit"></p><div id="hits" class="grid"></div></section>
<section><h2>Tìm bằng tiếng Việt vẫn được giữ</h2><p>Ba truy vấn kiểm tra luồng tìm văn bản; xem ảnh đầu tiên bên dưới để đánh giá nội dung. Đây chưa phải benchmark tiếng Việt.</p><div id="language" class="grid"></div></section>
<p class="dim">Ảnh và video kiểm thử được lưu cục bộ, không nằm trong gói ứng dụng. Chế độ đối chiếu hiển thị đoạn xem quanh khung đã kiểm tra; độ dài đó chưa phải toàn bộ lần xuất hiện.</p></main><script>
const $=id=>document.getElementById(id);let data;
const labels={'uniform_0.1fps':'Mốc đều mỗi 10 giây','uniform_0.5fps':'Mốc đều mỗi 2 giây','hybrid_similar':'Mỗi 2 giây + chuyển cảnh · tương tự','hybrid_detail':'Mỗi 2 giây + chuyển cảnh · đối chiếu'};
const el=(tag,text)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;return x};
const time=s=>`${Math.floor(s/60)}:${(s%60).toFixed(2).padStart(5,'0')}`;
function render(){const q=data.queries.find(q=>q.id===$('query').value),method=$('method').value,r=q.results[method];$('reference').src=q.image;$('caption').textContent=q.category==='known_source'?`${q.kind==='full_frame'?'Toàn cảnh':'Vùng chơi game'} · mốc nguồn ${time(q.source_t)} · ${q.held_out?'ảnh không trùng frame index':'ảnh trùng frame index, loại khỏi thống kê giữ ngoài'}`:'Ảnh đối chứng từ DAVIS, ngoài nguồn video người dùng';
$('status').textContent=`${r.hits.length} kết quả · ${r.indexed_frames} khung trong chỉ mục`;const a=r.verification;$('audit').textContent=a?(a.status==='insufficient_detail'?'Ảnh thiếu chi tiết để đối chiếu.':`Đã đối chiếu ${a.checked}/${a.candidates_total} ứng viên; ${a.unavailable} khung không đọc được.`):'Xếp hạng theo độ tương đồng; điểm không phải xác suất đúng.';
$('hits').replaceChildren();for(const [i,h] of r.hits.entries()){const f=el('figure'),img=el('img');img.src=h.thumb;img.alt=`Kết quả ${i+1} tại ${time(h.peak_t)}`;img.loading='lazy';f.append(img,el('figcaption',`#${i+1} · ${time(h.peak_t)} · cosine ${h.score.toFixed(3)}`));if(q.category==='known_source'){const near=Math.abs(h.peak_t-q.source_t)<=data.protocol.known_source_tolerance_seconds;const mark=el('p',near?'Về gần mốc nguồn':'Mốc khác — đối chiếu nội dung');mark.className=near?'good':'dim';f.append(mark)}$('hits').append(f)}if(!r.hits.length)$('hits').append(el('p','Chưa có khung đủ bằng chứng trong các ứng viên đã kiểm tra.'))}
fetch('review.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{data=d;$('overview').textContent=`Đã xử lý ${time(d.source_seconds)} video, ${d.indexed_frames} khung; 9 mốc truy vấn × 2 cách chọn ảnh, cùng 6 ảnh đối chứng ngoài nguồn. Các mốc được chọn trước khi chạy tìm kiếm.`;const head=el('tr');for(const t of ['Cách tìm','Toàn cảnh về mốc / top 5','Crop về mốc / top 5','Ảnh đối chứng có kết quả'])head.append(el('th',t));$('table').append(head);
for(const [key,s] of Object.entries(d.summary)){const row=el('tr');for(const t of [labels[key],`${s.full_frame.known_source_top5}/${s.full_frame.queries}`,`${s.gameplay_region.known_source_top5}/${s.gameplay_region.queries}`,`${s.foreign_reference_returned}/${s.foreign_reference_queries}`])row.append(el('td',t));$('table').append(row);const option=el('option',labels[key]);option.value=key;$('method').append(option)}
for(const q of d.queries){const option=el('option',q.category==='known_source'?`${time(q.source_t)} · ${q.kind==='full_frame'?'Toàn cảnh':'Vùng chơi game'}`:q.id);option.value=q.id;$('query').append(option)}
for(const q of d.language){const f=el('figure');f.append(el('h3',q.text));if(q.hits.length){const h=q.hits[0],img=el('img');img.src=h.thumb;img.alt=q.text;f.append(img,el('figcaption',`Kết quả đầu · ${time(h.peak_t)} · cosine ${h.score.toFixed(3)}`))}else f.append(el('p','Không có kết quả'));$('language').append(f)}
$('method').value='hybrid_detail';render()}).catch(e=>$('status').textContent='Không tải được kết quả: '+e.message);$('query').onchange=render;$('method').onchange=render;
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "queries", "davis", "library", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    manifest = json.loads((args.queries / "manifest.json").read_text(encoding="utf-8"))
    images = {q["id"]: args.queries / q["image"] for q in manifest["queries"]}
    images.update({q["id"]: args.davis / q["image"] for q in json.loads((args.davis / "manifest.json").read_text(encoding="utf-8"))["queries"]})
    for sub in ("queries", "frames"):
        (args.output / sub).mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect((args.library / "library.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    try:
        thumbnails = dict(db.execute("SELECT id,thumb FROM frames"))
    finally:
        db.close()
    for query in report["queries"]:
        query["image"] = "queries/" + query["id"] + ".png"
        shutil.copyfile(images[query["id"]], args.output / query["image"])
        for result in query["results"].values():
            for hit in result["hits"]:
                hit["thumb"] = f"frames/{hit['frame_id']}.jpg"
                shutil.copyfile(args.library / "thumbnails" / thumbnails[hit["frame_id"]], args.output / hit["thumb"])
    for query in report["language"]:
        for hit in query["hits"]:
            hit["thumb"] = f"frames/{hit['frame_id']}.jpg"
            shutil.copyfile(args.library / "thumbnails" / thumbnails[hit["frame_id"]], args.output / hit["thumb"])
    (args.output / "review.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    (args.output / "index.html").write_text(HTML, encoding="utf-8")
    print(json.dumps({"queries": len(report["queries"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
