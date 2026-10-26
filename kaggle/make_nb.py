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
R={'started':time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()), 'precision':'DINOv3 fp16 autocast; SAM 3 autocast fp16 (bf16 fallback)', 'stages':{}, 'errors':[]}
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
r'''# EG2 weights: flat 'eg2files__a@b' -> /tmp/eg2/a/b
EG2=None
for p in glob.glob('/kaggle/input/**/eg2files__*', recursive=True):
    rel=os.path.basename(p).split('__',1)[1].replace('@','/'); d=os.path.join('/tmp/eg2',os.path.dirname(rel)); os.makedirs(d,exist_ok=True)
    if not os.path.exists('/tmp/eg2/'+rel): os.symlink(p,'/tmp/eg2/'+rel)
    EG2='/tmp/eg2'
R['eg2_path']=EG2
run('install','pip -q install faiss-cpu pycocotools psutil && git clone -q https://github.com/facebookresearch/sam3.git /tmp/sam3 && pip -q install -e /tmp/sam3 && cd /tmp/sam3 && git rev-parse HEAD', 900)
run('install_eg2','pip -q install --no-deps --target /tmp/eglib "transformers==5.20.2" "sentence-transformers==6.2.0" "huggingface_hub==1.33.0" "tokenizers==0.23.2" "safetensors==0.8.0" && python -c "import sys;sys.path.insert(0,\'/tmp/eglib\');import transformers,sentence_transformers as s;print(transformers.__version__,s.__version__)"', 900)
os.environ['SAM3_BPE']='/tmp/sam3/sam3/assets/bpe_simple_vocab_16e6.txt.gz'
print({k:(v['rc'],v['tail'][-200:]) for k,v in R['stages'].items() if k.startswith('install')})''',
r'''run('data','wget -q https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip -O /tmp/davis.zip && mkdir -p data && unzip -q /tmp/davis.zip -d data && rm /tmp/davis.zip && python scripts/prepare_davis.py && python scripts/make_hard_queries.py && python scripts/add_distractors.py', 1200)
print(R['stages']['data']['rc'])''',
r'''T0=time.time(); BUDGET=100*60
def left(): return BUDGET-(time.time()-T0)
SAN=["import json, glob, sys, os, time, torch; sys.path.insert(0, '.')",
 "from PIL import Image",
 "from vsearch.core import sample_frames",
 "from vsearch.sam3_regions import SAM3Regions",
 "sam = SAM3Regions(); out = {'load_info': sam.load_info, 'precision': os.environ.get('DE12_SAM_DTYPE','fp16'), 'prompts': list(sam.prompts), 'threshold': sam.th}",
 "im = Image.open('/tmp/sam3/assets/images/truck.jpg').convert('RGB')",
 "out['official_truck'] = sam.raw(im, 'truck'); out['official_object'] = sam.raw(im, 'object')",
 "fr = [im for v in sorted(glob.glob('data/davis_bench_large/videos/*.mp4'))[:5] for _, im in list(sample_frames(v, 1.0))[:1]]",
 "t = time.time(); n = [len(sam(f)) for f in fr]; out['davis5_boxes'] = n; out['davis5_s_per_frame'] = round((time.time()-t)/len(fr), 3)",
 "out['ok'] = out['official_truck']['n_ge_th'] > 0 and sum(n) > 0",
 "json.dump(out, open('results/sanity.json', 'w'), indent=1); print(out)"]
open('sanity.py','w').write(chr(10).join(SAN))
SAM_OK=False; R['note']='v6: EG2-only run (SAM results are in v5); DINOv3 grid rerun for same-run comparison'
save(); print(R.get('gpu_bench'))''',
r'''R['index']={}; R['eval']={}; R['skipped']=[]
SETS={'large70':'data/davis_bench_large','small10':'data/davis_bench'}; D=os.environ['DINOV3_PATH']
EGENV='PYTHONPATH=/tmp/eglib TRANSFORMERS_VERBOSITY=error'
for sn,B in SETS.items():
    reg='grid+sam3' if SAM_OK else 'grid'
    run(f'index_dinov3_{sn}',f'python scripts/build_index.py --videos {B}/videos --out data/{sn}_d3 --model {D} --regions {reg}', 2400)
    if EG2: run(f'index_eg2_{sn}',f'{EGENV} python scripts/build_index.py --videos {B}/videos --out data/{sn}_eg2 --model {EG2} --regions grid', 1500)
for d in glob.glob('data/*_d3')+glob.glob('data/*_eg2'):
    try: m=json.load(open(d+'/meta.json')); m.pop('meta',None); R['index'][os.path.basename(d)]=m
    except Exception as e: R['errors'].append(f'index meta {d}: {e!r}')
save(); print(R['index'])''',
r'''for sn,B in SETS.items():
  for Q in ['object_hard','object']:
    jobs=[('dinov3', f'--index data/{sn}_d3 --modes '+('frame,region,both,sam,frame+sam,fuse' if SAM_OK else 'frame,region,both'), '')]
    if SAM_OK: jobs.append(('dinov3_rerank_sam_top20', f'--index data/{sn}_d3 --modes both --rerank samidx --videos {B}/videos', ''))
    if EG2: jobs.append(('eg2', f'--index data/{sn}_eg2 --modes frame,region,both', EGENV))
    for tag,cmd,env in jobs:
        if not os.path.exists(cmd.split()[1]+'/meta.json'): R['skipped'].append(f'{sn}/{tag}/{Q} (no index)'); continue
        if left()<120: R['skipped'].append(f'{sn}/{tag}/{Q} (time)'); continue
        o=f'results/E_{sn}_{tag}_{Q}.json'; run(f'eval_{sn}_{tag}_{Q}', f'{env} python scripts/evaluate.py {cmd} --queries {B}/queries_{Q}.json --out {o}', max(120,int(left())))
        try: R['eval'][f'{sn}/{tag}/{Q}']=json.load(open(o))['results']
        except Exception as e: R['errors'].append(f'eval {sn}/{tag}/{Q}: {e!r}')
        save()
R['finished']=time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()); save()
print(json.dumps(R['eval'], indent=1)[:4000]); print('errors', R['errors'], 'skipped', R['skipped'])
for f in os.listdir('/kaggle/working'):
    if f!='de12_results.json': subprocess.run(['rm','-rf','/kaggle/working/'+f])
print(os.listdir('/kaggle/working'))''']
nb = {"cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Đề 12 – Kaggle T4 v6 (EG2 vs DINOv3, 70+10 video; SAM in v5): hybrid DINOv3 + SAM 3 (sam3.pt, fp16/bf16 autocast, class-vocabulary prompts, masked-crop region vectors) + EmbeddingGemma 2 baseline; 70 + 10 video. Built with DINOv3.\n", "Trọng số offline từ dataset private `holilihu/de7-weights`. Toàn bộ kết quả → 1 file `/kaggle/working/de12_results.json`; dữ liệu làm việc ở /tmp."]}] + \
        [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": [c]} for c in cells],
      "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open("kaggle/de12_kaggle.ipynb", "w"), indent=1)
print("ok", len(CODE))
