#!/usr/bin/env python3
"""Maintainer-only audit of versioned code bundled inside npm distributions."""
import collections,concurrent.futures,json,pathlib,urllib.request,yaml
import vendor
R=pathlib.Path(__file__).resolve().parents[1]
installed=json.loads((R/'audit/packages.json').read_text());already={(p['name'],p['version']) for p in installed}
origins=collections.defaultdict(list);items={};keys=[]
for parent in installed:
    for identifier in parent['embedded_identifiers']:
        name,version=identifier.split('_',1)[0].rsplit('@',1);name=name.replace('+','/')
        key=(name,version);origins[key].append({'host':parent['name']+'@'+parent['version'],'identifier':identifier,'kind':'observed-bundle-module'})
        if key not in already:items[key]=[name,version,[],[],None]
        if parent['name']=='jiti':keys.append(name+'@'+version)
lock=yaml.safe_load((R/'audit/upstream/jiti-pnpm-lock.yaml').read_text());seeds=[k for k in lock['snapshots'] if k.split('(',1)[0] in keys];seen=set();queue=collections.deque(seeds)
while queue:
    key=queue.popleft()
    if key in seen:continue
    seen.add(key)
    for kind in ['dependencies','optionalDependencies']:
        for n,v in lock['snapshots'][key].get(kind,{}).items():queue.append(n+'@'+v)
for key in seen:
    name,version=key.split('(',1)[0].rsplit('@',1);pair=(name,version)
    origins[pair].append({'host':'jiti@2.7.0','identifier':key,'kind':'upstream-runtime-closure-not-proof-of-inclusion'})
    if pair not in already:items[pair]=[name,version,[],[],None]
out=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    for i,p in enumerate(pool.map(lambda item:vendor.acquire(item,'vendor/embedded-upstream'),items.values()),1):
        p['origins']=origins[(p['name'],p['version'])];out.append(p)
        if i%25==0:print('Supplemental bundled code',i,'/',len(items),flush=True)
out.sort(key=lambda p:(p['name'],p['version']))
(R/'audit/embedded-packages.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(R/'audit/embedded-origins.json').write_text(json.dumps([{'name':n,'version':v,'origins':o} for (n,v),o in sorted(origins.items())],indent=2)+'\n')
payload=collections.defaultdict(list)
for p in installed+out:payload[p['name']].append(p['version'])
request=urllib.request.Request('https://registry.npmjs.org/-/npm/v1/security/advisories/bulk',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(request,timeout=60) as response:alerts=json.load(response)
(R/'audit/all-advisories.json').write_text(json.dumps(alerts,indent=2)+'\n')
print(json.dumps({'supplemental':len(out),'upstream_jiti_closure':len(seen),'advisories':alerts},ensure_ascii=False),flush=True)
