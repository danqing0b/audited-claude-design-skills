#!/usr/bin/env python3
import concurrent.futures,hashlib,json,pathlib,urllib.request
R=pathlib.Path(__file__).resolve().parents[1];COMMIT='2c5958ecac7cee2b583967a2c4981d0f4a75c579'
def one(item):
    url='https://raw.githubusercontent.com/anthropics/skills/'+COMMIT+'/'+item['path']
    with urllib.request.urlopen(url,timeout=60) as response:data=response.read()
    assert len(data)==item['size']
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['gitblob']
    p=R/item['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    return dict(item,sha256=hashlib.sha256(data).hexdigest())
items=json.loads((R/'audit/upstream-assets.json').read_text())
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(one,items))
(R/'audit/upstream-assets.json').write_text(json.dumps(out,indent=2)+'\n');print('Verified upstream data assets',len(out))
