import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const R='/workspace/scratch/1c70cef937ec/qa19-p8';
const f=(await fs.readdir(R+'/source')).find(n=>n.startsWith('09'));
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(R+'/source/'+f));
console.log((await w.inspect({kind:'sheet',include:'id,name',maxChars:1800})).ndjson);
const p=await w.render({sheetName:'Пример заполнения',range:'A15:C25',scale:1.5,format:'png'});
await fs.writeFile(R+'/internal/excel-before.png',new Uint8Array(await p.arrayBuffer()));
