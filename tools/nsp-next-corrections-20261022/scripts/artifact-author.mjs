import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const plan=JSON.parse(await fs.readFile(process.argv[2],'utf8'));
const root='/workspace/scratch/6ca5fc64b5d2/';
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(root+'next-corrections/products-storage/'+plan.path));
const views=[...new Set(plan.edits.map(e=>e.sheet))];
for(let i=0;i<views.length;i++){
 const b=await w.render({sheetName:views[i],range:views[i]==='Сводка'?'A1:F20':'A1:H12',scale:1,format:'png'});
 await fs.writeFile(root+'next-qa/proof/'+plan.issue+'-before-'+i+'.png',new Uint8Array(await b.arrayBuffer()));
}
for(const e of plan.edits){const r=w.worksheets.getItem(e.sheet).getRange(e.cell);if(typeof e.value==='string'&&e.value.startsWith('='))r.formulas=[[e.value]];else r.values=[[e.value]];}
w.recalculate();
const errors=await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:30},maxChars:4000});
await fs.writeFile(root+'next-qa/proof/'+plan.issue+'-scan.json',errors.ndjson);
for(let i=0;i<views.length;i++){
 const b=await w.render({sheetName:views[i],range:views[i]==='Сводка'?'A1:F20':'A1:H12',scale:1,format:'png'});
 await fs.writeFile(root+'next-qa/proof/'+plan.issue+'-after-'+i+'.png',new Uint8Array(await b.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(w)).save(root+'next-qa/authored/'+plan.issue+'.xlsx');
console.log('AUTHORED',plan.issue,plan.edits.length);
