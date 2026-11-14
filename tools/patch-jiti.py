#!/usr/bin/env python3
"""Deterministic local security patch. Does not fetch or run third-party code."""
import base64,copy,csv,gzip,hashlib,io,json,pathlib,tarfile
R=pathlib.Path(__file__).resolve().parents[1]
archive=R/'vendor/npm/jiti@2.7.0.tgz';original=R/'.audit-source/upstream/jiti@2.7.0.tgz';original.parent.mkdir(parents=True,exist_ok=True)
if not original.exists():original.write_bytes(archive.read_bytes())
raw=original.read_bytes();records=json.loads((R/'audit/packages.json').read_text());rec=next(p for p in records if p['name']=='jiti')
registry=json.loads((R/'audit/registry-package-lock.json').read_text())['packages']['node_modules/jiti']['integrity']
assert 'sha512-'+base64.b64encode(hashlib.sha512(raw).digest()).decode()==registry
before=None;after=None;output=io.BytesIO()
with gzip.GzipFile(fileobj=output,mode='wb',mtime=0,filename='') as gz:
    with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as dest:
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as source:
            for m in source.getmembers():
                content=source.extractfile(m).read() if m.isfile() else None
                if m.name=='package/dist/babel.cjs':
                    before=content.decode();start=before.index('if(!1!==t.inputSourceMap)');end=before.index('return new n.default(t,{code:r,ast:a,inputMap:u})',start)
                    removed=before[start:end]
                    assert removed.count('readFileSync')==1 and 'source' in removed.lower() and removed.endswith(')}}')
                    after=before[:start]+'/* Local security patch: never load input source maps. */'+before[end:]
                    assert after.count('if(!1!==t.inputSourceMap)')==0
                    content=after.encode()
                    patch={'package':'jiti','version':'2.7.0','upstream_integrity':registry,'upstream_sha256':hashlib.sha256(raw).hexdigest(),'file':'dist/babel.cjs','before_sha256':hashlib.sha256(before.encode()).hexdigest(),'after_sha256':hashlib.sha256(content).hexdigest(),'removed_code':removed,'reason':'GHSA-4x5r-pxfx-6jf8: disable both inline and external input source maps in the bundled Babel normalizer; no external-map filesystem read remains in this path.'}
                if m.name=='package/package.json':
                    d=json.loads(content);d['x-audited-local-patch']='disable-input-source-maps-v1';content=(json.dumps(d,indent=2)+'\n').encode()
                entry=copy.copy(m)
                if content is not None:entry.size=len(content)
                dest.addfile(entry,io.BytesIO(content) if content is not None else None)
assert before is not None and after is not None
patched=output.getvalue();archive.write_bytes(patched)
integrity='sha512-'+base64.b64encode(hashlib.sha512(patched).digest()).decode();patch['patched_integrity']=integrity;patch['patched_sha256']=hashlib.sha256(patched).hexdigest()
lock=json.loads((R/'package-lock.json').read_text())
for path,value in lock['packages'].items():
    if path.split('node_modules/')[-1]=='jiti':value['integrity']=integrity
(R/'package-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
rec['upstream_integrity']=registry;rec['local_patch']='disable-input-source-maps-v1';rec['integrity']=integrity;rec['sha256']=patch['patched_sha256'];rec['bytes']=len(patched)
rec['security_fix']='GHSA-4x5r-pxfx-6jf8 locally patched; upstream version alone still matches advisory.'
(R/'audit/packages.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
(R/'audit/jiti-local-patch.json').write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n')
with (R/'audit/packages.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['name','version','archive','integrity','sha256','source_exempt','install_hooks','binary_files','signals','patch'])
    for p in records:w.writerow([p['name'],p['version'],p['archive'],p['integrity'],p['sha256'],p['source_exempt'],json.dumps(p['lifecycle']),len(p['binaries']),len(p['hits']),p.get('local_patch','')])
print('Patched bundled Babel source map input path:',patch['patched_sha256'])
