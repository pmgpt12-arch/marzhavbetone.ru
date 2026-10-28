import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const base=new URL('.',import.meta.url).pathname;
const plan=JSON.parse(await fs.readFile(base+'proof/XLSX_CASES.json','utf8'));
await fs.mkdir(base+'proof/lo-inputs',{recursive:true});
for(let i=0;i<plan.cases.length;i++){
 const c=plan.cases[i];const w=await SpreadsheetFile.importXlsx(await FileBlob.load(base+'output/02-reestr-izyatiy-po-obektu.xlsx'));const s=w.worksheets.getItem('Изъятия');
 for(const [cell,value]of Object.entries(c.inputs))s.getRange(cell).values=[[value]];
 w.recalculate();await(await SpreadsheetFile.exportXlsx(w)).save(base+'proof/lo-inputs/'+String(i+1).padStart(2,'0')+'-'+c.name+'.xlsx');
}
console.log('LO_FIXTURES',plan.cases.length,'BUYER_SOURCE_UNCHANGED');
