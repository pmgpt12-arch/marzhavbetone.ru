import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const O=process.env.NSP_QA03_ROOT;if(!O)throw Error('NSP_QA03_ROOT required');
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(O+'/source/02-reestr-uderzhaniy-po-obektu.xlsx'));w.recalculate();
await fs.mkdir(O+'/proof',{recursive:true});
const b=await w.render({sheetName:'Реестр удержаний',range:'A1:N15',scale:1,format:'png'});await fs.writeFile(O+'/proof/source-xlsx.png',new Uint8Array(await b.arrayBuffer()));
console.log((await w.inspect({kind:'table',range:'Реестр удержаний!D15:L15',include:'values,formulas',maxChars:1200})).ndjson);
