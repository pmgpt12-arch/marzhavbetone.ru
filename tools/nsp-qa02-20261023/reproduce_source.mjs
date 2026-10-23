import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile}from '@oai/artifact-tool';
const O='/workspace/scratch/4c2f1716d70e/qa02-repo/tools/nsp-qa02-20261023';
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(O+'/source/02-kalkulyator-sroka-oplaty.xlsx'));const s=w.worksheets.getItemAt(0);
const D=x=>(Date.parse(x+'T00:00:00Z')-Date.UTC(1899,11,30))/86400000;
const cases=[
 {name:'weekend',event:'2026-10-16',days:2,type:'календарные',end:'2026-10-21',sum:100000,rate:.001,expected_due:D('2026-10-19'),expected_penalty:200},
 {name:'holiday',event:'2026-11-03',days:1,type:'рабочие',end:'2026-11-06',sum:100000,rate:.001,expected_due:D('2026-11-05'),expected_penalty:100},
 {name:'fractional-days',event:'2026-10-01',days:1.5,type:'календарные',end:'2026-10-21',sum:100000,rate:.001,expected:'REJECT_FRACTION'},
 {name:'negative-debt',event:'2026-10-01',days:5,type:'календарные',end:'2026-10-21',sum:-100000,rate:.001,expected:'REJECT_NEGATIVE'},
 {name:'negative-rate',event:'2026-10-01',days:5,type:'календарные',end:'2026-10-21',sum:100000,rate:-.001,expected:'REJECT_NEGATIVE'},
 {name:'partial-paid-before-period',event:'2026-10-01',days:5,type:'календарные',end:'2026-10-21',sum:100000,rate:.001,payment:40000,expected_penalty:900}
];const results=[];
for(const c of cases){s.getRange('B4').values=[[c.days]];s.getRange('B5').values=[[c.type]];s.getRange('B6').values=[[D(c.event)]];s.getRange('B10').values=[[c.rate]];s.getRange('B11').values=[[c.sum]];
 // Test-only frozen clock replaces TODAY dependency, not the defective due/base/rate formulas.
 s.getRange('B8').formulas=[['=MAX(0,'+D(c.end)+'-B7)']];w.recalculate();
 results.push({...c,actual:{due:s.getRange('B7').values[0][0],days:s.getRange('B8').values[0][0],penalty:s.getRange('B12').values[0][0]}});
}
await fs.writeFile(O+'/proof/SOURCE_REPRODUCTION.json',JSON.stringify({engine:'artifact-tool; six source defect reproductions, not native acceptance',clock_control:'Only B8 TODAY clock replaced by a fixed serial in memory; no source or public file written',source_sha256:'4c23401703d64eae9818919dfa4598c2944f1bd7816ed2255bd9d38061ad4077',results},null,2));
console.log(JSON.stringify(results.map(x=>({name:x.name,actual:x.actual,expected:x.expected??x.expected_penalty}))));
