import fs from 'node:fs/promises';
import {build,reset,apply} from './build_workbook.mjs';
const O='/workspace/scratch/4c2f1716d70e/qa02-repo/tools/nsp-qa02-20261023';
const data=JSON.parse(await fs.readFile(O+'/CASES.json','utf8'));
const w=await build();const results=[];
for(const c of data.cases){reset(w);apply(w,c.inputs);w.recalculate();const checks=[];
 for(const [sheet,expect]of Object.entries(c.expected))for(const [cell,expected]of Object.entries(expect)){
  const actual=w.worksheets.getItem(sheet).getRange(cell).values[0][0];const pass=typeof expected==='number'?typeof actual==='number'&&Math.abs(actual-expected)<0.005:actual===expected;
  checks.push({sheet,cell,expected,actual,pass});
 }
 results.push({name:c.name,status:checks.every(x=>x.pass)?'PASS':'FAIL',checks});
 if(results.at(-1).status==='FAIL')console.log(JSON.stringify(results.at(-1)));
}
await fs.writeFile(O+'/proof/ARTIFACT_SCENARIOS.json',JSON.stringify({engine:'@oai/artifact-tool',cases:results.length,checks:results.reduce((a,r)=>a+r.checks.length,0),passed:results.filter(r=>r.status==='PASS').length,results},null,2));
console.log('CASES',results.length,'PASS',results.filter(r=>r.status==='PASS').length);
if(results.some(r=>r.status!=='PASS'))process.exitCode=1;
