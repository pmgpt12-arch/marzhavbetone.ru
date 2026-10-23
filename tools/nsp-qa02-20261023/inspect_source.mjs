import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root='/workspace/scratch/4c2f1716d70e/qa02-repo/tools/nsp-qa02-20261023';
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(root+'/source/02-kalkulyator-sroka-oplaty.xlsx'));
console.log((await w.inspect({kind:'sheet',include:'id,name',maxChars:1000})).ndjson);
const s=w.worksheets.getItemAt(0);
const p=await w.render({sheetName:s.name,range:'A1:C12',scale:1.5,format:'png'});
await fs.writeFile('/workspace/scratch/4c2f1716d70e/qa02-inputs/source-xlsx.png',new Uint8Array(await p.arrayBuffer()));
console.log((await w.inspect({kind:'region',sheetId:s.name,range:'A1:C12',maxChars:2000})).ndjson);
