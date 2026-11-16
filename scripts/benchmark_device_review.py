"""Compare production CPU FP32 and CUDA BF16, alternating five fresh indexes."""
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from benchmark_review import measured_index, WORK, settings
from desktop.backend.inference import Encoder
from sentence_transformers import SentenceTransformer
import numpy as np
import torch
from PIL import Image

torch.set_num_threads(8)
encoders = {}
for device, dtype in [('cpu', torch.float32), ('cuda', torch.bfloat16)]:
    encoder = Encoder(WORK, settings['model_path'], settings['vision_tokens'])
    # Same constructor arguments as Encoder.ensure; only device is explicit for A/B.
    begin = time.perf_counter()
    encoder.model = SentenceTransformer(settings['model_path'], device=device,
        config_kwargs={'audio_config': None}, model_kwargs={'dtype': dtype})
    encoder.device, encoder.state = device, 'ready'
    encoder.images([Image.new('RGB',(640,360),(50,70,100))]*4)
    encoders[device] = encoder
    print('Loaded and warmed',device,round(time.perf_counter()-begin,2),flush=True)

probe = WORK/'index-probe-40s.mp4'
report={'settings':settings,'runs':[],'failure_count':0,'model_load_excluded':True}
for trial in range(5):
    vectors={}
    for device in ('cpu','cuda'):
        result, vector=measured_index(encoders[device],probe,WORK/f'device-pairs/{trial}-{device}',True)
        result['device']=device
        result['trial']=trial
        vectors[device]=vector
        report['runs'].append(result)
        print(trial,device,round(result['wall_seconds'],3),flush=True)
    cosines=np.sum(vectors['cpu']*vectors['cuda'],axis=1)
    report.setdefault('agreement',[]).append({'min_cosine':float(cosines.min()),'mean_cosine':float(cosines.mean())})
    assert cosines.min()>.99
    (WORK/'device-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for device in encoders:
    values=[r['wall_seconds'] for r in report['runs'] if r['device']==device]
    print(device,'median',statistics.median(values),'range',min(values),max(values),flush=True)
