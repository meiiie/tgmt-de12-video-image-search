import subprocess,json,time,os,sys
H=os.environ['H']
p=subprocess.Popen([H+'/digup','search-service','sample','--index','index'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
def r(o):
    p.stdin.write(json.dumps(o)+'\n');p.stdin.flush()
    while True:
        l=p.stdout.readline()
        if not l: return None
        try: d=json.loads(l)
        except: continue
        if d.get('id')==o['id']: return d
t=time.time();print('prewarm',r({'id':1,'op':'prewarm'}));
# wait encoder ready
while True:
    s=r({'id':2,'op':'status'})
    if s.get('encoder') in('ready','unavailable'):break
    time.sleep(0.5)
print('encoder ready after %.1fs'%(time.time()-t), s.get('encoder'))
for i,q in enumerate(["zebra","animal with black and white stripes","a red car on a highway","a cat sleeping on a sofa"]):
    t=time.time();d=r({'id':10+i,'op':'search','q':q,'limit':5,'meaning':True})
    print(repr(q),'wall %.0f ms'%((time.time()-t)*1000),'ms=',d.get('ms'),[(os.path.basename(h['path']),round(h.get('cosine') or 0,3),h.get('loc'),h.get('info')) for h in d.get('hits',[])])
r({'id':99,'op':'quit'})
