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
ok = Wt.get('dinov3')  # v7: SAM not rerun (numbers in v5)
if not ok: R['errors'].append('weights missing / sha mismatch'); save(); raise SystemExit('stop')
os.environ['DINOV3_PATH']=Wt['dinov3']; os.environ['SAM3_CKPT']=Wt.get('sam3_ckpt') or ''; os.environ['SAM3_STRICT']='1'
run('nvidia_smi','nvidia-smi --query-gpu=name,memory.total --format=csv'); print(R['weights'])'''.replace('@@CODE@@', CODE),
r'''# EG2 weights: flat 'eg2files__a@b' -> /tmp/eg2/a/b. v7 FIX: dataset flattened '1_Pooling/config.json' as
# '1_Poolingconfig.json' (no '@') -> Pooling got no config -> "missing embedding_dimension" in v5/v6.
EG2=None; FIX={'1_Poolingconfig.json':'1_Pooling/config.json','2_Normalizeconfig.json':'2_Normalize/config.json'}
for p in glob.glob('/kaggle/input/**/eg2files__*', recursive=True):
    rel=os.path.basename(p).split('__',1)[1].replace('@','/'); rel=FIX.get(rel,rel); d=os.path.join('/tmp/eg2',os.path.dirname(rel)); os.makedirs(d,exist_ok=True)
    if not os.path.exists('/tmp/eg2/'+rel): os.symlink(p,'/tmp/eg2/'+rel)
    EG2='/tmp/eg2'
R['eg2_path']=EG2; R['eg2_files']=sorted(os.path.relpath(x,'/tmp/eg2') for x in glob.glob('/tmp/eg2/**',recursive=True) if os.path.isfile(x)) if EG2 else []
run('install','pip -q install faiss-cpu pycocotools psutil', 600)
run('install_eg2','pip -q install --no-deps --target /tmp/eglib "transformers==5.20.2" "sentence-transformers==6.2.0" "huggingface_hub==1.33.0" "tokenizers==0.23.2" "safetensors==0.8.0" && python -c "import sys;sys.path.insert(0,\'/tmp/eglib\');import torch,torchvision,transformers,sentence_transformers as s;print(torch.__version__,torchvision.__version__,transformers.__version__,s.__version__)"', 900)
EGENV='PYTHONPATH=/tmp/eglib TRANSFORMERS_VERBOSITY=error'
run('eg2_smoke', EGENV+' python -c "import sys;sys.path.insert(0,\'.\');from vsearch.core import Embedder;from PIL import Image;e=Embedder(\'/tmp/eg2\');v=e([Image.new(\'RGB\',(224,224),(120,30,30))]);print(v.shape,float((v*v).sum()))"', 900)
print({k:(v['rc'],v['tail'][-300:]) for k,v in R['stages'].items()})''',
r'''run('data','wget -q https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip -O /tmp/davis.zip && mkdir -p data && unzip -q /tmp/davis.zip -d data && rm /tmp/davis.zip && python scripts/prepare_davis.py && python scripts/make_hard_queries.py && python scripts/add_distractors.py', 1200)
print(R['stages']['data']['rc'])''',
r'''T0=time.time(); BUDGET=100*60  # all post-setup work; whole kernel < 2h
def left(): return BUDGET-(time.time()-T0)
R['note']='v7: EG2 (fixed Pooling config path) vs DINOv3 frame+grid; SAM not rerun (v5)'; R['index']={}; R['eval']={}; R['skipped']=[]
SETS={'large70':'data/davis_bench_large','small10':'data/davis_bench'}; D=os.environ['DINOV3_PATH']
for sn,B in SETS.items(): run(f'index_dinov3_{sn}',f'python scripts/build_index.py --videos {B}/videos --out data/{sn}_d3 --model {D} --regions grid', 900)
save()''',
r'''# EG2 indexing, own cell, <=5400 s total, per-video cache in /kaggle/working/eg2_cache (survives timeout; resumable)
C='/kaggle/working/eg2_cache'; T1=time.time(); EG_LIMIT=5400
def eg_left(): return min(EG_LIMIT-(time.time()-T1), left()-900)  # keep ~15 min for evals
for sn,reg in [('large70','none'),('small10','none'),('large70','grid')]:
    if not EG2 or R['stages'].get('eg2_smoke',{}).get('rc')!=0: R['skipped'].append('eg2 (no weights / smoke failed)'); break
    if eg_left()<300: R['skipped'].append(f'index_eg2_{sn}_{reg} (time)'); continue
    run(f'index_eg2_{sn}_{reg}', f'{EGENV} python scripts/build_index_cached.py --videos {SETS[sn]}/videos --out data/{sn}_eg2_{reg} --model {EG2} --regions {reg} --cache {C}/{sn}', int(eg_left()))
    R['eg2_cached_videos_'+sn]=len(glob.glob(f'{C}/{sn}/*.json')); save()
for d in sorted(glob.glob('data/*_d3')+glob.glob('data/*_eg2_*')):
    try: m=json.load(open(d+'/meta.json')); m.pop('meta',None); R['index'][os.path.basename(d)]=m
    except Exception as e: R['errors'].append(f'index meta {d}: {e!r}')
save(); print(R['index'], R['skipped'])''',
r'''for sn,B in SETS.items():
  for Q in (['object_hard','object'] if sn=='large70' else ['object_hard']):
    jobs=[('dinov3', f'--index data/{sn}_d3 --modes frame,region,both', ''),
          ('eg2_frame', f'--index data/{sn}_eg2_none --modes frame', EGENV),
          ('eg2_grid', f'--index data/{sn}_eg2_grid --modes frame,region,both', EGENV)]
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
nb = {"cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Đề 12 – Kaggle T4 v7 (EG2 vs DINOv3, 70+10 video; EG2 Pooling-config fix; SAM in v5): hybrid DINOv3 + SAM 3 (sam3.pt, fp16/bf16 autocast, class-vocabulary prompts, masked-crop region vectors) + EmbeddingGemma 2 baseline; 70 + 10 video. Built with DINOv3.\n", "Trọng số offline từ dataset private `holilihu/de7-weights`. Toàn bộ kết quả → 1 file `/kaggle/working/de12_results.json`; dữ liệu làm việc ở /tmp."]}] + \
        [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": [c]} for c in cells],
      "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open("kaggle/de12_kaggle.ipynb", "w"), indent=1)
print("ok", len(CODE))
