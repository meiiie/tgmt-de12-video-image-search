"""Build kaggle/de12_kaggle.ipynb: code tarball embedded; work in /tmp/de12 (NOT /kaggle/working);
the only output is /kaggle/working/de12_results.json (avoids 429 from listing many output files)."""
import base64, io, json, tarfile, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as t:
    for d in ["vsearch", "scripts"]:
        t.add(d, filter=lambda x: None if "__pycache__" in x.name else x)
CODE = base64.b64encode(buf.getvalue()).decode()
cells = [r'''import os, sys, io, base64, tarfile, json, time, subprocess, traceback, glob
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', DE12_FP16='1')
OUT='/kaggle/working/de12_results.json'; W0='/tmp/de12'; os.makedirs(W0, exist_ok=True); os.chdir(W0)
R={'started':time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()), 'precision':'fp16 autocast (DINOv3 + SAM 3.1)', 'stages':{}, 'errors':[]}
def save():
    json.dump(R, open(OUT+'.tmp','w'), indent=1); os.replace(OUT+'.tmp', OUT)
def run(name, cmd, timeout=3000):
    t=time.time()
    try:
        p=subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=W0)
        R['stages'][name]={'rc':p.returncode,'sec':round(time.time()-t,1),'tail':(p.stdout+p.stderr)[-3000:]}
        if p.returncode: R['errors'].append(name)
    except subprocess.TimeoutExpired as e:
        R['stages'][name]={'rc':'timeout','sec':round(time.time()-t,1)}; R['errors'].append(name+':timeout')
    save()
CODE = '@@CODE@@'
tarfile.open(fileobj=io.BytesIO(base64.b64decode(CODE)), mode='r:gz').extractall('.')
sys.path.insert(0, W0); os.makedirs('results', exist_ok=True)
from vsearch.weights import discover
t=time.time(); Wt = discover('/kaggle/input', '/tmp/w'); Wt['assemble_s']=round(time.time()-t,1)
R['weights']={k:v for k,v in Wt.items() if k!='layout'}
ok = Wt.get('dinov3') and Wt.get('sam3_ckpt') and Wt.get('sam3_sha256_ok', False)
if not ok: R['errors'].append('weights missing / sha mismatch'); save(); raise SystemExit('stop')
os.environ['DINOV3_PATH']=Wt['dinov3']; os.environ['SAM3_CKPT']=Wt.get('sam3_ckpt') or ''; os.environ['SAM3_STRICT']='1'
run('nvidia_smi','nvidia-smi --query-gpu=name,memory.total --format=csv'); print(R['weights'])'''.replace('@@CODE@@', CODE),
r'''run('install','pip -q install faiss-cpu pycocotools psutil && git clone -q https://github.com/facebookresearch/sam3.git /tmp/sam3 && pip -q install -e /tmp/sam3 && cd /tmp/sam3 && git rev-parse HEAD', 900)
print(R['stages']['install'])''',
r'''run('data','wget -q https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip -O /tmp/davis.zip && mkdir -p data && unzip -q /tmp/davis.zip -d data && rm /tmp/davis.zip && python scripts/prepare_davis.py && python scripts/make_hard_queries.py && python scripts/add_distractors.py', 1200)
print(R['stages']['data']['rc'], R['stages']['data'].get('sec'))''',
r'''T0=time.time(); BUDGET=52*60  # stop starting new stages after ~52 min (kernel cap 1h)
def left(): return BUDGET-(time.time()-T0)
SAN=["import json, glob, sys, os; sys.path.insert(0, '.')",
 "from vsearch.core import sample_frames",
 "from vsearch.sam3_regions import SAM3Regions",
 "fr = [im for v in sorted(glob.glob('data/davis_bench_large/videos/*.mp4'))[:5] for _, im in list(sample_frames(v, 1.0))[:1]]",
 "sam = SAM3Regions(min_score=0.3); n = [len(sam(f)) for f in fr]",
 "json.dump({'load_info': sam.load_info, 'boxes_per_frame': n, 'ok': sum(n) > 0}, open('results/sanity.json', 'w'), indent=1)"]
open('sanity.py','w').write(chr(10).join(SAN))
run('sam_sanity','python sanity.py', 600)
try: R['sam_sanity']=json.load(open('results/sanity.json'))
except Exception as e: R['sam_sanity']={'ok':False,'error':repr(e)}
SAM_OK=bool(R['sam_sanity'].get('ok')); save(); print(R['sam_sanity'])
if not SAM_OK: R['errors'].append('SAM sanity: 0 boxes or load failure -> SAM stages skipped')
run('gpu_bench','python scripts/gpu_bench.py', 900)
try: R['gpu_bench']=json.load(open('results/gpu_bench.json'))
except Exception as e: R['errors'].append('gpu_bench json: %r'%e)
save(); print(R.get('gpu_bench'))''',
r'''R['index']={}; R['eval']={}; R['skipped']=[]
SETS={'large70':'data/davis_bench_large','small10':'data/davis_bench'}; D=os.environ['DINOV3_PATH']
for sn,B in SETS.items():
    run(f'index_grid_{sn}',f'python scripts/build_index.py --videos {B}/videos --out data/{sn}_grid --model {D} --regions grid', 900)
    if SAM_OK and left()>600: run(f'index_sam3_{sn}',f'python scripts/build_index.py --videos {B}/videos --out data/{sn}_sam3 --model {D} --regions sam3', 1200)
    elif SAM_OK: R['skipped'].append(f'index_sam3_{sn} (time)')
for d in glob.glob('data/*_grid')+glob.glob('data/*_sam3'):
    try: m=json.load(open(d+'/meta.json')); m.pop('meta',None); R['index'][os.path.basename(d)]=m
    except Exception as e: R['errors'].append(f'index meta {d}: {e!r}')
save(); print(R['index'])''',
r'''for sn,B in SETS.items():
  for Q in ['object_hard','object']:
    jobs=[('dinov3_grid',f'--index data/{sn}_grid')]
    if SAM_OK: jobs+=[('sam3_region',f'--index data/{sn}_sam3'),('rerank_sam3_top20',f'--index data/{sn}_grid --modes both --rerank sam3 --videos {B}/videos')]
    for tag,cmd in jobs:
        if not os.path.exists(cmd.split()[1]+'/meta.json'): R['skipped'].append(f'{sn}/{tag}/{Q} (no index)'); continue
        if tag.startswith('rerank') and left()<300: R['skipped'].append(f'{sn}/{tag}/{Q} (time)'); continue
        o=f'results/E_{sn}_{tag}_{Q}.json'; run(f'eval_{sn}_{tag}_{Q}', f'python scripts/evaluate.py {cmd} --queries {B}/queries_{Q}.json --out {o}', max(120,int(left())))
        try: R['eval'][f'{sn}/{tag}/{Q}']=json.load(open(o))['results']
        except Exception as e: R['errors'].append(f'eval {sn}/{tag}/{Q}: {e!r}')
        save()
R['finished']=time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()); save()
print(json.dumps(R['eval'], indent=1)[:4000]); print('errors', R['errors'], 'skipped', R['skipped'])
for f in os.listdir('/kaggle/working'):
    if f!='de12_results.json': subprocess.run(['rm','-rf','/kaggle/working/'+f])
print(os.listdir('/kaggle/working'))''']
nb = {"cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Đề 12 – Kaggle T4 v3: DINOv3 + SAM 3 image ckpt sam3.pt (fp16), sanity 5 frames, region / re-rank top-20 (proposal cache), 70 + 10 video. Built with DINOv3.\n", "Trọng số offline từ dataset private `holilihu/de7-weights`. Toàn bộ kết quả → 1 file `/kaggle/working/de12_results.json`; dữ liệu làm việc ở /tmp."]}] + \
        [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": [c]} for c in cells],
      "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open("kaggle/de12_kaggle.ipynb", "w"), indent=1)
print("ok", len(CODE))
