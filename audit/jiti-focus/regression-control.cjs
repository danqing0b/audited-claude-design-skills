const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const root = fs.mkdtempSync(path.join(os.tmpdir(),'jiti-regression-control-'));
const canary = path.join(root,'private.map');
const secret = 'AUDIT_FAKE_SOURCE_CONTENT_347ab';
fs.writeFileSync(canary,JSON.stringify({version:3,sources:['private.ts'],names:[],mappings:'AAAA',sourcesContent:[secret]}));
const originalTransform = require('/tmp/unpatched-babel.cjs');
const patchedTransform = require('/app/node_modules/jiti/dist/babel.cjs');
function run(transform) {
  const originalRead=fs.readFileSync;let reads=0;
  fs.readFileSync=function(file,...args){if(String(file)===canary)reads++;return originalRead.call(this,file,...args);};
  try {
    const result=transform({source:`export const answer: number = 42;\n//# sourceMappingURL=${canary}`,filename:path.join(root,'input.ts'),ts:true,babel:{filename:path.join(root,'input.ts'),sourceMaps:'inline'}});
    if(result.error)throw result.error;
    const mapMatch=result.code.match(/sourceMappingURL=data:application\/json[^,]*,([^\s]+)/);
    const sourceMap=mapMatch?Buffer.from(mapMatch[1],'base64').toString('utf8'):'';
    return {canaryFileReads:reads,outputMapContainsFakeSecret:sourceMap.includes(secret)};
  }finally{fs.readFileSync=originalRead;}
}
const before=run(originalTransform),after=run(patchedTransform);
if(before.canaryFileReads!==1||after.canaryFileReads!==0||!before.outputMapContainsFakeSecret||after.outputMapContainsFakeSecret)throw new Error('Regression control did not demonstrate the expected before/after behavior');
console.log(JSON.stringify({before,after,realSecretsUsed:false,uid:process.getuid(),node:process.version,networkInterfaces:Object.keys(os.networkInterfaces())}));
fs.rmSync(root,{recursive:true,force:true});
