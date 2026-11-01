"""Build a local, silent-by-default review lab from measured audio candidates."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


PAGE = r'''<!doctype html>
<html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FrameAtlas · Lab chọn clip</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101715;color:#e9eee8;font:15px/1.55 system-ui,sans-serif}
header,main{max-width:1220px;margin:auto;padding:24px}header{border-bottom:1px solid #32443b}
.eyebrow{color:#adc7a5;font-size:12px;letter-spacing:.16em}h1{font-size:30px;margin:8px 0}p{color:#b9c6be;max-width:850px}
.layout{display:grid;grid-template-columns:320px 1fr;gap:24px}.list{display:grid;gap:9px;align-content:start}
button{font:inherit;border:1px solid #476253;border-radius:8px;background:#20382c;color:inherit;padding:10px 14px;cursor:pointer}
button:hover,button[aria-current=true]{border-color:#c3dd9a;background:#304b36}button:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #e9ce8d;outline-offset:3px}
.candidate{text-align:left;display:grid;gap:4px;width:100%}.candidate small,.muted{color:#b1c0b6}.candidate strong{font-variant-numeric:tabular-nums}
video{width:100%;max-height:520px;background:#000;border-radius:12px}h2{font-size:20px;margin:14px 0 8px}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.note{border-left:3px solid #cdb67f;padding:8px 14px;background:#282a20}
textarea{display:block;width:100%;min-height:80px;margin-top:8px;background:#18251e;color:inherit;border:1px solid #476253;border-radius:8px;padding:12px;font:inherit}
#summary{color:#c3dd9a}footer{margin-top:24px;font-size:13px;color:#b1c0b6}a{color:#c3dd9a}@media(max-width:760px){.layout{grid-template-columns:1fr}.list{grid-template-columns:repeat(2,minmax(0,1fr))}header,main{padding:16px}}
</style>
<header><div class="eyebrow">FRAMEATLAS / RESEARCH LAB</div><h1>Từ video dài đến danh sách cần xem</h1>
<p>EG2 đã tìm các cửa sổ âm thanh gần với mô tả. Mỗi đoạn có thêm ngữ cảnh trước và sau. Bạn quyết định đoạn nào đáng dựng; điểm tương đồng không phải điểm hài hước.</p>
<div id="summary" role="status" aria-live="polite"></div></header>
<main><div class="layout"><nav class="list" aria-label="Ứng viên làm clip" id="list"></nav><section>
<video id="player" controls muted playsinline preload="metadata" aria-label="Xem ứng viên"></video>
<h2 id="title"></h2><p id="reason"></p><p class="note" id="details"></p>
<div class="actions"><button id="keep">Giữ để dựng</button><button id="drop">Bỏ qua</button><button id="context">Cần thêm ngữ cảnh</button><button id="reset">Chưa duyệt</button></div>
<label for="notes">Ghi chú: điều gì đáng giữ, có bị cắt mất câu chuyện không?</label><textarea id="notes" placeholder="Ví dụ: có tiếng cười nhưng chưa rõ chuyện gì gây cười…"></textarea>
<div class="actions"><button id="export">Xuất đánh giá JSON</button><button id="csv">Xuất danh sách đã giữ CSV</button></div>
<footer>Video chỉ nằm trên máy. Bấm phát và bật âm thanh khi thuận tiện. Ngữ cảnh ở đây là khoảng cắt cố định để kiểm tra, chưa phải biên tập tự động theo câu chuyện. Đánh giá lưu trong trình duyệt; xuất JSON để giữ một bản độc lập.</footer>
</section></div></main>
<script type="application/json" id="data">__DATA__</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent), key='frameatlas-highlight-lab-'+data.identity;
let reviews={};try{reviews=JSON.parse(localStorage.getItem(key)||'{}')}catch{}
let current=data.items[0];const $=id=>document.getElementById(id);
const time=t=>`${Math.floor(t/3600).toString().padStart(2,'0')}:${Math.floor(t%3600/60).toString().padStart(2,'0')}:${Math.floor(t%60).toString().padStart(2,'0')}`;
const names={keep:'Đã giữ',drop:'Đã bỏ',context:'Cần ngữ cảnh',unreviewed:'Chưa duyệt'};
function save(){localStorage.setItem(key,JSON.stringify(reviews));renderList()}
function renderList(){
 $('list').replaceChildren();data.items.forEach(item=>{const button=document.createElement('button');button.className='candidate';button.setAttribute('aria-current',String(item.id===current.id));
 const name=document.createElement('strong');name.textContent=time(item.signal_start);const label=document.createElement('small');label.textContent=names[reviews[item.id]?.status||'unreviewed']+' · '+item.reasons.map(r=>r.label).join(' / ');
 button.append(name,label);button.onclick=()=>select(item);$('list').append(button)});
 const kept=data.items.filter(x=>reviews[x.id]?.status==='keep').length,done=data.items.filter(x=>reviews[x.id]?.status && reviews[x.id].status!=='unreviewed').length;
 $('summary').textContent=`${data.items.length} ứng viên · ${done} đã duyệt · ${kept} giữ để dựng · Nguồn ${time(data.source_seconds)}`;
}
function select(item){current=item;$('player').pause();$('player').muted=true;$('player').src=item.clip;$('player').load();
 $('title').textContent='Ứng viên tại '+time(item.signal_start);$('reason').textContent='Tìm thấy qua: '+item.reasons.map(r=>r.label).join(' / ');
 $('details').textContent=`Đoạn nguồn ${time(item.review_start)}–${time(item.review_end)}. Cửa sổ âm thanh được chấm điểm: ${time(item.signal_start)}–${time(item.signal_end)}. Trạng thái: ${names[reviews[item.id]?.status||'unreviewed']}.`;
 $('notes').value=reviews[item.id]?.notes||'';renderList();
}
for(const [button,status] of [['keep','keep'],['drop','drop'],['context','context'],['reset','unreviewed']]){$(button).onclick=()=>{reviews[current.id]={status,notes:$('notes').value,updated:new Date().toISOString()};save();$('details').textContent=`Đoạn nguồn ${time(current.review_start)}–${time(current.review_end)}. Trạng thái: ${names[status]}.`}}
$('notes').oninput=()=>{reviews[current.id]={...(reviews[current.id]||{status:'unreviewed'}),notes:$('notes').value};save()};
function download(name,body,type){const url=URL.createObjectURL(new Blob([body],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
$('export').onclick=()=>download('highlight-review.json',JSON.stringify({...data,reviews},null,2),'application/json');
$('csv').onclick=()=>{const cell=s=>{let value=String(s??'');if(/^[=+@\-]/.test(value))value="'"+value;return '"'+value.replaceAll('"','""')+'"'};
 const rows=[['id','source_start_seconds','source_end_seconds','notes'],...data.items.filter(x=>reviews[x.id]?.status==='keep').map(x=>[x.id,x.review_start,x.review_end,reviews[x.id].notes])];
 download('selected-clips.csv','\ufeff'+rows.map(r=>r.map(cell).join(',')).join('\r\n'),'text/csv;charset=utf-8')};
select(current);
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads((args.lab / "input.json").read_text(encoding="utf-8"))
    report = json.loads((args.lab / "candidates.json").read_text(encoding="utf-8"))
    if not report["complete"]:
        raise ValueError("Finish audio indexing before building the review lab")
    stat = Path(source["source"]).stat()
    if (stat.st_size, stat.st_mtime_ns) != (source["size"], source["mtime_ns"]):
        raise ValueError("Source changed since analysis")
    identity = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()[:16]
    args.output.mkdir(parents=True, exist_ok=True)
    clips = args.output / "clips"
    clips.mkdir(exist_ok=True)
    labels = {"laugh_en": "Tiếng cười · EN", "laugh_vi": "Tiếng cười · VI",
              "excited_en": "Phản ứng phấn khích", "funny_vi": "Hài hước · thử nghiệm", "music_en": "Âm nhạc · đối chiếu"}
    by_start = {}
    for query in report["queries"]:
        if query["id"] not in labels:
            continue
        count = 2 if query["id"] in {"funny_vi", "music_en"} else 3
        for item in query["results"][:count]:
            start = item["signal_start"]
            if start not in by_start:
                by_start[start] = {**item, "id": f"{identity}-{start}", "reasons": []}
            by_start[start]["reasons"].append({"query": query["id"], "label": labels[query["id"]], "similarity": item["similarity"]})
    items = sorted(by_start.values(), key=lambda x: x["signal_start"])
    for item in items:
        target = clips / (item["id"] + ".mp4")
        if not target.exists():
            temporary = target.with_suffix(".tmp.mp4")
            subprocess.run([str(args.ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-ss", str(item["review_start"]), "-i", source["source"],
                "-t", str(item["review_end"] - item["review_start"]),
                "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=960:-2", "-r", "30",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-threads", "2",
                "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(temporary)], check=True)
            temporary.replace(target)
        item["clip"] = "clips/" + target.name
        print(json.dumps({"clip": target.name, "bytes": target.stat().st_size}), flush=True)
    data = {"identity": identity, "source_seconds": report["audio_seconds"], "items": items,
            "method": "EG2 audio 10s windows; fixed context; human review pending"}
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    (args.output / "index.html").write_text(PAGE.replace("__DATA__", payload), encoding="utf-8")
    (args.output / "review-manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ready": str(args.output), "candidates": len(items)}), flush=True)


if __name__ == "__main__":
    main()
