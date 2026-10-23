import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const out=new URL('./print-diagnostic/',import.meta.url).pathname;
await fs.mkdir(out,{recursive:true});
for(const [tag,name] of [['latin','PrintTest'],['cyrillic','Печать']]){
 const w=Workbook.create(),s=w.worksheets.add(name);
 s.getRange('A1:B3').values=[['INCLUDED-'+tag,'OUTSIDE-AREA-'+tag],[123,456],['Expected: only column A','This column must not print']];
 s.getRange('A1:B3').format.font={name:'Arial',size:12,color:'#222222'};
 s.getRange('A1:B3').format.columnWidth=35;s.getRange('A1:B3').format.rowHeight=26;
 s.getRange('A1:B1').format.font.bold=true;s.showGridLines=false;
 w.recalculate();
 await fs.writeFile(out+tag+'-inspect.json',(await w.inspect({kind:'table',range:name+'!A1:B3',include:'values,formulas',maxChars:2000})).ndjson);
 const img=await w.render({sheetName:name,range:'A1:B3',scale:1.5,format:'png'});await fs.writeFile(out+tag+'.png',new Uint8Array(await img.arrayBuffer()));
 await(await SpreadsheetFile.exportXlsx(w)).save(out+tag+'-base.xlsx');
}
