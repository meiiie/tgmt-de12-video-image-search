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
ok = Wt.get('dinov3') and Wt.get('sam31_ckpt') and Wt.get('sam31_sha256_ok', True)
if not ok: R['errors'].append('weights missing / sha mismatch'); save(); raise SystemExit('stop')
os.environ['DINOV3_PATH']=Wt['dinov3']; os.environ['SAM3_CKPT']=Wt['sam31_ckpt']
run('nvidia_smi','nvidia-smi --query-gpu=name,memory.total --format=csv'); print(R['weights'])'''.replace('@@CODE@@', CODE),
r'''run('install','pip -q install faiss-cpu pycocotools psutil && git clone -q https://github.com/facebookresearch/sam3.git /tmp/sam3 && pip -q install -e /tmp/sam3 && cd /tmp/sam3 && git rev-parse HEAD', 900)
print(R['stages']['install'])''',
r'''run('data','wget -q https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip -O /tmp/davis.zip && mkdir -p data && unzip -q /tmp/davis.zip -d data && rm /tmp/davis.zip && python scripts/prepare_davis.py && python scripts/make_hard_queries.py && python scripts/add_distractors.py', 1200)
print(R['stages']['data']['rc'], R['stages']['data'].get('sec'))''',
r'''run('gpu_bench','python scripts/gpu_bench.py', 1200)
try: R['gpu_bench']=json.load(open('results/gpu_bench.json'))
except Exception as e: R['errors'].append('gpu_bench json: %r'%e)
save(); print(R.get('gpu_bench'))''',
r'''B='data/davis_bench_large'; D=os.environ['DINOV3_PATH']
run('index_grid',f'python scripts/build_index.py --videos {B}/videos --out data/L_dinov3 --model {D} --regions grid', 1800)
run('index_sam3',f'python scripts/build_index.py --videos {B}/videos --out data/L_dinov3_sam3 --model {D} --regions sam3', 2700)
R['index']={}
for d in glob.glob('data/L_*'):
    try: m=json.load(open(d+'/meta.json')); m.pop('meta',None); R['index'][os.path.basename(d)]=m
    except Exception as e: R['errors'].append(f'index meta {d}: {e!r}')
save(); print(R['index'])''',
r'''R['eval']={}
for Q in ['object_hard','object']:
    for tag,cmd in [('dinov3_grid',f'--index data/L_dinov3'),('dinov3_sam3region',f'--index data/L_dinov3_sam3'),
                    ('dinov3_rerank_sam3_top20',f'--index data/L_dinov3 --modes both --rerank sam3 --videos {B}/videos')]:
        o=f'results/K_{tag}_{Q}.json'; run(f'eval_{tag}_{Q}', f'python scripts/evaluate.py {cmd} --queries {B}/queries_{Q}.json --out {o}', 2400)
        try: R['eval'][f'{tag}/{Q}']=json.load(open(o))['results']
        except Exception as e: R['errors'].append(f'eval {tag}/{Q}: {e!r}')
        save()
R['finished']=time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()); save()
print(json.dumps(R['eval'], indent=1)[:4000]); print('errors', R['errors'])
for f in os.listdir('/kaggle/working'):
    if f!='de12_results.json': subprocess.run(['rm','-rf','/kaggle/working/'+f])
print(os.listdir('/kaggle/working'))''']
nb = {"cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Đề 12 – Kaggle T4 v2: DINOv3 + SAM 3.1 (fp16) region / re-rank top-20, 70 video. Built with DINOv3.\n", "Trọng số offline từ dataset private `holilihu/de7-weights`. Toàn bộ kết quả → 1 file `/kaggle/working/de12_results.json`; dữ liệu làm việc ở /tmp."]}] + \
        [{"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": [c]} for c in cells],
      "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}, "nbformat": 4, "nbformat_minor": 5}
json.dump(nb, open("kaggle/de12_kaggle.ipynb", "w"), indent=1)
print("ok", len(CODE))
