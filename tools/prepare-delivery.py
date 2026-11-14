#!/usr/bin/env python3
"""Package reviewed local assets and remove non-delivered build-only reference archives."""
import argparse,base64,copy,gzip,hashlib,io,json,pathlib,re,shutil,tarfile
R=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--p5-archive',type=pathlib.Path,required=True);args=parser.parse_args()
refs=json.loads((R/'audit/embedded-packages.json').read_text());kept=[];excluded=[]
for p in refs:
    if any(o['kind']=='observed-bundle-module' for o in p['origins']):kept.append(p)
    else:
        (R/p['archive']).unlink(missing_ok=True)
        excluded.append({'name':p['name'],'version':p['version'],'origins':p['origins'],'status':'upstream build closure only; not observed in delivered bundle; not an installed dependency; archive excluded from delivery'})
excluded_file=R/'audit/excluded-upstream-build-packages.json'
if excluded_file.exists():excluded.extend(json.loads(excluded_file.read_text()))
excluded=list({(p['name'],p['version']):p for p in excluded}.values())
excluded_file.write_text(json.dumps(excluded,ensure_ascii=False,indent=2)+'\n')

# Patch the supplemental Babel reference archive as well as jiti's actual runtime bundle.
p=next(p for p in kept if p['name']=='@babel/core');file=R/p['archive'];raw=file.read_bytes()
backup=R/'.audit-source/upstream/@babel__core@7.29.0.tgz';backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():backup.write_bytes(raw)
raw=backup.read_bytes();output=io.BytesIO();patch=None
with gzip.GzipFile(fileobj=output,mode='wb',filename='',mtime=0) as gz:
    with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as dst:
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as src:
            for m in src.getmembers():
                data=src.extractfile(m).read() if m.isfile() else None
                if m.name=='package/lib/transformation/normalize-file.js':
                    before=data.decode();start=before.index('  if (options.inputSourceMap !== false) {');end=before.index('  return new _file.default(options, {',start)
                    removed=before[start:end];assert removed.count('readFileSync')==1
                    after=before[:start]+'  // Audited local patch: input source maps are disabled.\n'+before[end:];data=after.encode()
                    patch={'package':'@babel/core@7.29.0','type':'supplemental reference archive; not installed independently','file':'lib/transformation/normalize-file.js','removed_code':removed,'before_sha256':hashlib.sha256(before.encode()).hexdigest(),'after_sha256':hashlib.sha256(data).hexdigest(),'upstream_archive_sha256':hashlib.sha256(raw).hexdigest()}
                if m.name=='package/package.json':
                    d=json.loads(data);d['x-audited-local-patch']='disable-input-source-maps-v1';data=(json.dumps(d,indent=2)+'\n').encode()
                entry=copy.copy(m)
                if data is not None:entry.size=len(data)
                dst.addfile(entry,io.BytesIO(data) if data is not None else None)
assert patch
patched=output.getvalue();file.write_bytes(patched);p['upstream_integrity']=p.get('upstream_integrity',p['integrity']);p['integrity']='sha512-'+base64.b64encode(hashlib.sha512(patched).digest()).decode();p['sha256']=hashlib.sha256(patched).hexdigest();p['bytes']=len(patched);p['local_patch']='disable-input-source-maps-v1'
(R/'audit/babel-reference-local-patch.json').write_text(json.dumps(patch,indent=2)+'\n')
(R/'audit/embedded-packages.json').write_text(json.dumps(kept,ensure_ascii=False,indent=2)+'\n')

runtime=R/'vendor/runtime';runtime.mkdir(exist_ok=True)
p5bytes=args.p5_archive.read_bytes();p5sri='sha512-'+base64.b64encode(hashlib.sha512(p5bytes).digest()).decode()
assert p5sri=='sha512-qrbT/44Dwm63ZtOKX/mp61pw+5yj6ijYLOmRv7p6zcfjbo83Vb0gVFEvW0kTLFu7hceWCig0HONo9F1bSlqbsQ=='
(runtime/'p5@1.7.0.tgz').write_bytes(p5bytes)
with tarfile.open(fileobj=io.BytesIO(p5bytes),mode='r:gz') as t:
    p5=t.extractfile('package/lib/p5.min.js').read().decode()
    licenses=[m for m in t.getmembers() if m.isfile() and 'license' in m.name.lower()]
    for m in licenses:(runtime/pathlib.PurePosixPath(m.name).name).write_bytes(t.extractfile(m).read())
viewer=R/'skills/algorithmic-art/templates/viewer.html';s=(R/'audit/upstream/algorithmic-art-viewer.html').read_text()
remote='<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.7.0/p5.min.js"></script>'
assert remote in s
s=s.replace(remote,'<script>\n'+p5.replace('</script','<\\/script')+'\n</script>')
s=re.sub(r'^\s*<link[^>]+https://fonts\.[^>]+>\s*$', '',s,flags=re.M)
s=s.replace('<head>', '<head>\n<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data: blob:; font-src data:; connect-src \'none\'; object-src \'none\'; base-uri \'none\'">',1)
viewer.write_text(s)
skill=R/'skills/algorithmic-art/SKILL.md';s=skill.read_text();s=s.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.7.0/p5.min.js"></script>','<!-- p5@1.7.0 is already embedded in templates/viewer.html. Preserve the reviewed inline copy; never fetch a CDN dependency. -->')
if '## Local security changes' not in s:s+='\n\n## Local security changes\n\nThis audited derivative embeds the reviewed p5 library and uses no Google Fonts requests. Keep the template self-contained. Do not add CDN imports or install dependencies while building.\n'
skill.write_text(s)
skill=R/'skills/canvas-design/SKILL.md';s=skill.read_text().replace('Download and use whatever fonts are needed to make this a reality.','Use the fonts already included in canvas-fonts; do not download fonts during installation or building.');skill.write_text(s)
record={'name':'p5','version':'1.7.0','archive':'vendor/runtime/p5@1.7.0.tgz','integrity':p5sri,'sha256':hashlib.sha256(p5bytes).hexdigest(),'inline_file':'skills/algorithmic-art/templates/viewer.html','inline_library_sha256':hashlib.sha256(p5.encode()).hexdigest(),'source_exempt':True,'review':'Previously reviewed known-library distribution; CDN bytes matched npm. Now embedded locally; no CDN code executes.'}
(R/'audit/runtime-assets.json').write_text(json.dumps([record],indent=2)+'\n')
print('Delivered supplemental archives',len(kept),'excluded build-only references',len(excluded),'embedded p5 bytes',len(p5.encode()))
