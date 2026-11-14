#!/usr/bin/env python3
import csv,datetime,hashlib,json,pathlib,urllib.parse
R=pathlib.Path(__file__).resolve().parents[1]
installed=json.loads((R/'audit/packages.json').read_text());embedded=json.loads((R/'audit/embedded-packages.json').read_text());runtime=json.loads((R/'audit/runtime-assets.json').read_text());all_packages=installed+embedded+runtime
def purl(name,version):return 'pkg:npm/'+urllib.parse.quote(name,safe='/')+'@'+version
components=[]
for p in all_packages:
    components.append({'type':'library','name':p['name'],'version':p['version'],'bom-ref':purl(p['name'],p['version']),'purl':purl(p['name'],p['version']),'hashes':[{'alg':'SHA-256','content':p['sha256']}],'properties':[{'name':'audit:archive','value':p['archive']},{'name':'audit:integrity','value':p['integrity']},{'name':'audit:local-patch','value':p.get('local_patch','none')},{'name':'audit:role','value':'installable' if p in installed else ('runtime-inline' if p in runtime else 'bundled-code-reference')}]})
lock=json.loads((R/'package-lock.json').read_text())['packages'];graph=json.loads((R/'audit/dependency-graph.json').read_text());deps={}
def ref(location):
    if location=='ROOT':return 'audited-claude-design-skills'
    p=lock[location];return purl(location.split('node_modules/')[-1],p['version'])
for e in graph['edges']:deps.setdefault(ref(e['from']),set()).add(ref(e['to']))
for p in embedded:
    for o in p['origins']:
        if o['kind']=='observed-bundle-module':
            name,version=o['host'].rsplit('@',1);deps.setdefault(purl(name,version),set()).add(purl(p['name'],p['version']))
for p in runtime:deps.setdefault('audited-claude-design-skills',set()).add(purl(p['name'],p['version']))
doc={'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'metadata':{'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'component':{'type':'application','name':'audited-claude-design-skills','version':'1.0.0','bom-ref':'audited-claude-design-skills'}},'components':components,'dependencies':[{'ref':k,'dependsOn':sorted(v)} for k,v in sorted(deps.items())],'vulnerabilities':[{'id':'GHSA-4x5r-pxfx-6jf8','source':{'name':'GitHub Advisory Database','url':'https://github.com/advisories/GHSA-4x5r-pxfx-6jf8'},'affects':[{'ref':purl('jiti','2.7.0')},{'ref':purl('@babel/core','7.29.0')}],'analysis':{'state':'resolved','response':['update'],'detail':'Explicit local patch removes bundled Babel input source-map loading; archive and file hashes are recorded. Upstream version retained for attribution. Before/after canary regression passed.'}}]}
(R/'audit/SBOM.cdx.json').write_text(json.dumps(doc,indent=2)+'\n')
for name,records in [('packages.csv',installed),('embedded-packages.csv',embedded),('all-packages.csv',all_packages)]:
    with (R/'audit'/name).open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['name','version','archive','sha256','integrity','source_exempt','local_patch'])
        for p in records:w.writerow([p['name'],p['version'],p['archive'],p['sha256'],p['integrity'],p.get('source_exempt',False),p.get('local_patch','')])
print('Exported SBOM components',len(components))
