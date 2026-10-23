import fs from 'node:fs/promises';
import{build,reset,apply,O}from'./build_workbook.mjs';
const data=JSON.parse(await fs.readFile(O+'/CASES.json','utf8'));const w=await build();const rows=[];
for(const c of data.cases){reset(w);apply(w,c.inputs);w.recalculate();const checks=[];
 for(const[sheet,cells]of Object.entries(c.expected))for(const[cell,expected]of Object.entries(cells)){
  const actual=w.worksheets.getItem(sheet).getRange(cell).values[0][0];const pass=typeof expected==='number'?typeof actual==='number'&&Math.abs(actual-expected)<.005:actual===expected;
  checks.push({sheet,cell,expected,actual,pass});
 }
 const row={name:c.name,status:checks.every(x=>x.pass)?'PASS':'FAIL',checks};rows.push(row);if(row.status==='FAIL')console.log(JSON.stringify(row));
}
await fs.writeFile(O+'/proof/ARTIFACT_SCENARIOS.json',JSON.stringify({engine:'@oai/artifact-tool',cases:rows.length,checks:rows.reduce((a,r)=>a+r.checks.length,0),passed:rows.filter(r=>r.status==='PASS').length,results:rows},null,2)+'\n');
console.log('CASES',rows.length,'PASS',rows.filter(x=>x.status==='PASS').length);if(rows.some(x=>x.status!=='PASS'))process.exitCode=1;
