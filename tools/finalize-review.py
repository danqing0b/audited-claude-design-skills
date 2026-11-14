#!/usr/bin/env python3
"""Record this review's explicit disposition and bind the audited bytes to the build gate."""
import collections,csv,hashlib,json,pathlib,datetime,tarfile
import vendor
R=pathlib.Path(__file__).resolve().parents[1]
installed=json.loads((R/'audit/packages.json').read_text());embedded=json.loads((R/'audit/embedded-packages.json').read_text());runtime=json.loads((R/'audit/runtime-assets.json').read_text())
# Refresh the sensitive-API scan for files changed by our documented local patches.
for packages in [installed,embedded]:
    for p in packages:
        if not p.get('local_patch'):continue
        changed='dist/babel.cjs' if p['name']=='jiti' else 'lib/transformation/normalize-file.js'
        p['hits']=[h for h in p['hits'] if h['path']!=changed]
        with tarfile.open(R/p['archive']) as t:content=t.extractfile('package/'+changed).read().decode()
        for lineno,line in enumerate(content.splitlines(),1):
            kinds=[k for k,rx in vendor.RX.items() if rx.search(line)]
            if kinds:p['hits'].append({'path':changed,'line':lineno,'kinds':kinds,'snippet':line[:800]})
        p['scan_after_local_patch']=True
(R/'audit/packages.json').write_text(json.dumps(installed,ensure_ascii=False,indent=2)+'\n')
(R/'audit/embedded-packages.json').write_text(json.dumps(embedded,ensure_ascii=False,indent=2)+'\n')
assert json.loads((R/'audit/advisories.json').read_text())=={},'new installed-package advisory requires review'
alerts=json.loads((R/'audit/all-advisories.json').read_text())
assert set(alerts)<= {'@babel/core','browserslist','baseline-browser-mapping'},'new embedded advisory requires manual review'
for p in installed+embedded:
    if p['name'] in ['jiti','@babel/core']:assert p.get('local_patch')=='disable-input-source-maps-v1'
signatures=json.loads((R/'audit/origin-signatures.json').read_text())
assert len(signatures)==len(installed)+len(embedded)+len(runtime)
assert all(any(s['verified'] for s in p['signatures']) for p in signatures)
lock=json.loads((R/'package-lock.json').read_text());packages=lock['packages'];edges=[];missing=[]
def resolve(parent,name):
    folder=parent
    while True:
        candidate=(folder+'/' if folder else '')+'node_modules/'+name
        if candidate in packages:return candidate
        if not folder:return None
        folder=folder.rsplit('/',1)[0] if '/' in folder else ''
for parent,p in packages.items():
    kinds=['dependencies','devDependencies','optionalDependencies'] if not parent else ['dependencies','optionalDependencies','peerDependencies']
    for kind in kinds:
        for name,spec in p.get(kind,{}).items():
            target=resolve(parent,name)
            if target:edges.append({'from':parent or 'ROOT','to':target,'kind':kind,'constraint':spec})
            elif kind!='peerDependencies' or not p.get('peerDependenciesMeta',{}).get(name,{}).get('optional',False):missing.append({'from':parent,'name':name,'kind':kind})
assert not missing,missing
(R/'audit/dependency-graph.json').write_text(json.dumps({'installedRecords':len(packages)-1,'uniqueInstalledPackages':len(installed),'edges':edges,'missing':missing},indent=2)+'\n')

origins=json.loads((R/'audit/embedded-origins.json').read_text());focus={(p['name'],p['version']) for p in origins if any(o['host']=='jiti@2.7.0' for o in p['origins'])}
excluded=json.loads((R/'audit/excluded-upstream-build-packages.json').read_text());excluded_keys={(p['name'],p['version']) for p in excluded}
lookup={(p['name'],p['version']):p for p in installed+embedded}
notes=[]
for key in sorted(focus):
    n,v=key
    if key in excluded_keys:
        detail='上游构建闭包补充记录，未在交付 bundle 中观察到；实际 helper-compilation-targets 为固定 stub。未作为交付安装依赖。'
        status='not-delivered-build-reference'
    else:
        p=lookup[key];status='focused-static-review'
        if n=='@babel/core':detail='重点追踪 sourceMappingURL → normalize-file → readFileSync → inputMap；已删除输入 source map 加载块。官方公告的行为与实际源码一致；未发现额外固定外传端点。'
        elif n.startswith('@babel/') or n=='babel-plugin-parameter-decorator':detail='已核对所交付转译器/语法插件/AST helper 的敏感行为。此链默认关闭 babelrc/configFile；插件转换源码 AST，不自动收集或发送凭据。配置加载与生成代码仅应处理可信输入。'
        elif n in ['get-tsconfig','mlly','pkg-types','get-package-type','resolve-pkg-maps']:detail='本地模块/配置路径解析与文件读取；读取对象由调用者的模块/配置路径决定。未发现自动安装包、固定网络上传地址或凭据搜索。'
        elif n in ['debug','ms','supports-color','has-flag']:detail='日志/终端颜色/时间格式化工具；debug 的浏览器存储用于日志开关。构建中关闭 JITI_DEBUG，未发现凭据外传路径。'
        else:detail='已校验归档、清单与敏感 API；映射/字符串/路径/编译辅助代码。未发现安装时副作用、固定上传端点或凭据窃取组合。'
    notes.append({'name':n,'version':v,'status':status,'note':detail})
(R/'audit/jiti-focus/package-review.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
with (R/'audit/jiti-focus/package-review.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['name','version','status','note']);w.writeheader();w.writerows(notes)

decisions=[
 {'advisory':'GHSA-4x5r-pxfx-6jf8','package':'@babel/core@7.29.0','status':'fixed-in-delivered-code','evidence':['audit/jiti-local-patch.json','audit/babel-reference-local-patch.json','tests/jiti-patch.test.mjs'],'note':'Official source-map vulnerability; input map loading removed in actual jiti bundle and reference archive. Raw version scanners may still match the retained upstream version.'},
 {'advisory':'GHSA-c83g-rgw3-j3cx','package':'browserslist@4.28.2','status':'not-delivered','note':'Upstream build-closure query only; jiti uses a helper-compilation-targets stub. This archive is excluded from delivery.'},
 {'advisory':'GHSA-73wf-gq98-2v4g','package':'browserslist@4.28.2','status':'not-delivered','note':'Same non-delivered upstream build reference.'},
 {'advisory':'GHSA-w5vr-8v7q-w6rv','package':'baseline-browser-mapping@2.10.27','status':'not-delivered','note':'Same stubbed, non-delivered Browserslist build path; archive excluded.'},
]
(R/'audit/advisory-dispositions.json').write_text(json.dumps(decisions,indent=2)+'\n')
extra=[]
for p in embedded+runtime:extra.append({'path':p['archive'],'sha256':p['sha256']})
for name in ['.npmrc','Dockerfile','vite.config.mjs','scripts/verify-vendor.mjs','scripts/offline-build.sh','scripts/build.mjs','scripts/single-file.mjs','scripts/init-project.mjs','audit/packages.json','audit/embedded-packages.json','audit/jiti-local-patch.json','audit/advisory-dispositions.json','skills/algorithmic-art/templates/viewer.html','skills/web-artifacts-builder/scripts/init-artifact.sh','skills/web-artifacts-builder/scripts/bundle-artifact.sh']:
    file=R/name;extra.append({'path':name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
review={'schemaVersion':1,'status':'accepted-static-audit','blockers':[],'reviewedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewMode':'Complete resolved install graph and bundled-code static review; sensitive paths manually traced. User-authorized well-known dependency depth exemptions remain outside the jiti-focused path. Not a proof of absence of unknown vulnerabilities.','installedPackages':len(installed),'supplementalBundleReferencePackages':len(embedded),'runtimeLibraryPackages':len(runtime),'jitiFocusedRecords':len(notes),'registrySignaturesVerified':len(signatures),'approvedIntegrities':{p['name']+'@'+p['version']:p['integrity'] for p in installed},'packageLockSha256':hashlib.sha256((R/'package-lock.json').read_bytes()).hexdigest(),'extraFiles':extra,'binaryLimit':'Native/WASM bytes verified and inventoried; not independently reverse engineered or reproducibly compiled.','dynamicValidation':'Required before repository publication; recorded separately in audit/validation.json.'}
(R/'audit/review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:review[k] for k in ['installedPackages','supplementalBundleReferencePackages','runtimeLibraryPackages','jitiFocusedRecords','registrySignaturesVerified']}))
