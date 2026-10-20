import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';
const source=process.argv[2], target=process.argv[3];
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:2000})).ndjson);
const layout=process.argv[5] ? JSON.parse(await fs.readFile(process.argv[5],'utf8')) : {sheets:{}};
for(const [part,change] of Object.entries(layout.sheets)){
 const sh=wb.worksheets.getItemAt(Number(part.match(/sheet(\d+)\.xml$/)[1])-1);
 for(const [target,source] of Object.entries(change.copy_style ?? {}))sh.getRange(target).copyFrom(sh.getRange(source),'all');
}
if(process.argv[4]){
 const patch=JSON.parse(await fs.readFile(process.argv[4],'utf8'));
 for(const change of patch){
  const sh=wb.worksheets.getItem(change.sheet);
  sh.getRange(change.cell).values=[[change.text]];
  sh.getRange(change.cell).format.autofitRows();
  if(change.rowHeight)sh.getRange(change.cell).format.rowHeight=change.rowHeight;
 }
}
if(process.argv[6]){
 const changes=JSON.parse(await fs.readFile(process.argv[6],'utf8'));
 for(const change of changes){
  const sh=wb.worksheets.getItemAt(Number(change.part.match(/sheet(\d+)\.xml$/)[1])-1);
  sh.getRange(change.cell).formulas=[[change.new]];
 }
}
for(const [part,change] of Object.entries(layout.sheets)){
 const sh=wb.worksheets.getItemAt(Number(part.match(/sheet(\d+)\.xml$/)[1])-1);
 for(const range of change.merges ?? [])sh.getRange(range).merge();
 for(const cell of change.wrap ?? [])sh.getRange(cell).format.wrapText=true;
 for(const [column,width] of Object.entries(change.columns ?? {}))sh.getRange(column+'1:'+column+'110').format.columnWidth=width;
 for(const [row,height] of Object.entries(change.row_heights ?? {}))sh.getRange('A'+row).format.rowHeight=height;
}
wb.recalculate();
if(process.env.MB_PREVIEW){
 const b=await wb.render({sheetName:wb.worksheets.getItemAt(0).name,range:'A1:J7',scale:1.5,format:'png'});
 await fs.writeFile(process.env.MB_PREVIEW,new Uint8Array(await b.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(target);
console.log('EXPORTED',target);
