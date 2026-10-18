import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';
const source=process.argv[2], target=process.argv[3];
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source));
console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:2000})).ndjson);
if(process.argv[4]){
 const patch=JSON.parse(await fs.readFile(process.argv[4],'utf8'));
 for(const change of patch){
  const sh=wb.worksheets.getItem(change.sheet);
  sh.getRange(change.cell).values=[[change.text]];
  if(change.rowHeight)sh.getRange(change.cell).format.rowHeight=change.rowHeight;
 }
}
wb.recalculate();
if(process.env.MB_PREVIEW){
 const b=await wb.render({sheetName:wb.worksheets.getItemAt(0).name,range:'A1:J7',scale:1.5,format:'png'});
 await fs.writeFile(process.env.MB_PREVIEW,new Uint8Array(await b.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(target);
console.log('EXPORTED',target);
