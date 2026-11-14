#!/usr/bin/env python3
"""Explicit maintainer-only network acquisition. Never imported by install/build."""
import argparse,base64,collections,concurrent.futures,csv,hashlib,io,json,pathlib,re,shutil,tarfile,urllib.request,os

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path(os.environ.get('AUDIT_WORK_DIR',str(ROOT/'.audit-source/packages')))
OLD=pathlib.Path(os.environ.get('AUDIT_CACHE_DIR',str(ROOT/'.audit-source/cache')))
def get(url):
    with urllib.request.urlopen(url,timeout=60) as r:return r.read()
def sri(raw,integrity):
    candidates=integrity.split()
    assert any(base64.b64encode(hashlib.new(x.split('-',1)[0],raw).digest()).decode()==x.split('-',1)[1] for x in candidates),'integrity mismatch'
def exempt(n):
    return n in {'react','react-dom','scheduler','react-refresh','typescript','vite','tailwindcss','postcss','lightningcss','rolldown'} or n.startswith(('@types/','@typescript/','@vitejs/','@tailwindcss/','@rolldown/','@oxc-project/','lightningcss-'))
PATTERNS={
 'process':r'child_process|\b(?:execSync|spawnSync|execFileSync|execFile|spawn)\s*\(',
 'network':r'\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(|\b(?:https?|net|tls|dns)\.(?:request|get|connect)\s*\(|require\([\x22\x27](?:node:)?(?:https?|net|tls|dns)[\x22\x27]\)',
 'dynamic-code':r'\beval\s*\(|\bnew\s+Function\s*\(|\bFunction\s*\([\x22\x27]|vm\.(?:runIn|compile)',
 'credential':r'\.npmrc|\.ssh\b|AWS_SECRET|AWS_ACCESS_KEY|GITHUB_TOKEN|NPM_TOKEN|process\.env\.(?:HOME|USERPROFILE)',
 'browser':r'dangerouslySetInnerHTML|document\.cookie|localStorage|sessionStorage|document\.write\s*\(',
 'filesystem':r'\b(?:readFileSync|writeFileSync|createReadStream|createWriteStream|readFile|writeFile|unlinkSync|rmSync)\s*\(',
}
RX={k:re.compile(v) for k,v in PATTERNS.items()}
def acquire(item,directory='vendor/npm'):
    name,version,paths,integrities,url=item;ident=name.replace('/','__')+'@'+version
    mp=OLD/'metadata'/(ident+'.json')
    meta=json.loads(mp.read_text()) if mp.exists() else json.loads(get('https://registry.npmjs.org/'+name.replace('/','%2f')+'/'+version))
    url=url or meta['dist']['tarball']
    archive=ROOT/directory/(ident+'.tgz');archive.parent.mkdir(parents=True,exist_ok=True)
    old=OLD/'tarballs'/(ident+'.tgz')
    if archive.exists():raw=archive.read_bytes()
    elif old.exists():raw=old.read_bytes();archive.write_bytes(raw)
    else:raw=get(url);archive.write_bytes(raw)
    for value in set(integrities+[meta['dist']['integrity']]):sri(raw,value)
    rec={'name':name,'version':version,'archive':str(archive.relative_to(ROOT)),'source_url':url,'integrity':meta['dist']['integrity'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'lock_paths':paths,'source_exempt':exempt(name),'repository':meta.get('repository'),'license':meta.get('license'),'gitHead':meta.get('gitHead'),'dependencies':meta.get('dependencies',{}),'optionalDependencies':meta.get('optionalDependencies',{}),'peerDependencies':meta.get('peerDependencies',{}),'scripts':meta.get('scripts',{}),'engines':meta.get('engines',{}),'lifecycle':{k:v for k,v in meta.get('scripts',{}).items() if k in ['preinstall','install','postinstall']},'files':0,'hits':[],'binaries':[],'embedded_identifiers':[],'manifest_differences':{}}
    dest=WORK/ident;dest.mkdir(parents=True,exist_ok=True);embedded=set()
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:
        for m in t.getmembers():
            parts=pathlib.PurePosixPath(m.name).parts
            if m.issym() or m.islnk() or '..' in parts or m.name.startswith('/') or m.isdev():raise ValueError('unsafe archive member '+m.name)
            if not m.isfile():continue
            relative='/'.join(parts[1:])
            if not relative:continue
            content=t.extractfile(m).read();rec['files']+=1
            target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            if content[:4] in [b'\x7fELF',b'\x00asm',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe'] or content[:2]==b'MZ' or relative.endswith(('.node','.wasm')):
                rec['binaries'].append({'path':relative,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)})
            if not relative.endswith(('.js','.cjs','.mjs','.ts','.tsx','.jsx','.sh','.py','.html','.json','.cc','.c','.cpp','.h')):continue
            if relative.endswith('.d.ts') or (relative.endswith('.json') and not relative.endswith('package.json')):continue
            text=content.decode('utf-8',errors='replace')
            embedded.update(re.findall(r'node_modules/\.pnpm/([^/\s"\\]+)/node_modules',text))
            # Scan known packages too; source exemption only affects manual review depth.
            for lineno,line in enumerate(text.splitlines(),1):
                kinds=[k for k,rx in RX.items() if rx.search(line)]
                if kinds:rec['hits'].append({'path':relative,'line':lineno,'kinds':kinds,'snippet':line[:800]})
    rec['embedded_identifiers']=sorted(embedded)
    local=json.loads((dest/'package.json').read_text())
    for k in ['name','version','dependencies','optionalDependencies','peerDependencies','scripts']:
        if local.get(k)!=meta.get(k):rec['manifest_differences'][k]={'registry':meta.get(k),'tarball':local.get(k)}
    return rec
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--allow-network-refresh',action='store_true');args=parser.parse_args()
    if not args.allow_network_refresh:parser.error('This maintenance operation requires --allow-network-refresh; ordinary builds remain offline.')
    lock_path=ROOT/'audit/registry-package-lock.json'
    if not lock_path.exists():shutil.copyfile(ROOT/'package-lock.json',lock_path)
    lock=json.loads(lock_path.read_text());entries={}
    for path,v in lock['packages'].items():
        if not path:continue
        n=path.split('node_modules/')[-1];key=(n,v['version'])
        e=entries.setdefault(key,[n,v['version'],[],[],v.get('resolved')]);e[2].append(path)
        if v.get('integrity'):e[3].append(v['integrity'])
    out=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        for i,record in enumerate(pool.map(acquire,entries.values()),1):
            out.append(record)
            if i%25==0:print('Acquired and scanned',i,'/',len(entries),flush=True)
    out.sort(key=lambda r:(r['name'],r['version']))
    (ROOT/'audit/packages.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    with (ROOT/'audit/packages.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['name','version','archive','integrity','sha256','source_exempt','install_hooks','binary_files','signals'])
        for r in out:writer.writerow([r['name'],r['version'],r['archive'],r['integrity'],r['sha256'],r['source_exempt'],json.dumps(r['lifecycle']),len(r['binaries']),len(r['hits'])])
    local_paths={(r['name'],r['version']):r['archive'] for r in out}
    for path,v in lock['packages'].items():
        if path and not v.get('inBundle'):v['resolved']='file:'+local_paths[(path.split('node_modules/')[-1],v['version'])]
    (ROOT/'package-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
    payload=collections.defaultdict(list)
    for r in out:payload[r['name']].append(r['version'])
    req=urllib.request.Request('https://registry.npmjs.org/-/npm/v1/security/advisories/bulk',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=60) as response:alerts=json.load(response)
    (ROOT/'audit/advisories.json').write_text(json.dumps(alerts,indent=2)+'\n')
    print(json.dumps({'packages':len(out),'archive_bytes':sum(r['bytes'] for r in out),'source_exempt':sum(r['source_exempt'] for r in out),'embedded':[(r['name'],r['embedded_identifiers']) for r in out if r['embedded_identifiers']],'alerts':alerts,'hooks':[(r['name'],r['lifecycle']) for r in out if r['lifecycle']]},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
