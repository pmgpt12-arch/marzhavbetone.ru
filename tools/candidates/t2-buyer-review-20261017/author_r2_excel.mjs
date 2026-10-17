import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const p=fileURLToPath(new URL('.',import.meta.url));
await fs.mkdir('/tmp/t2-author-0267',{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(p+'/r2-files/03-opis-peredavaemogo-komplekta.xlsx'));
const edits=JSON.parse(await fs.readFile(p+'/r2-excel-text-edits.json','utf8'));
if(process.argv.includes('--help-print')) {
 console.log(wb.help('worksheet.pageLayout',{include:'index,notes,examples',maxChars:5000}).ndjson);
 process.exit(0);
}
for(const [name,cells] of Object.entries(edits)) {
 const sh=wb.worksheets.getItem(name);
 for(const [address,value] of Object.entries(cells)) sh.getRange(address).values=[[value]];
}
wb.recalculate();
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},maxChars:2500})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save('/tmp/t2-author-0267/final-authored.xlsx');
await fs.writeFile('/tmp/t2-author-0267/final-instructions.png',new Uint8Array(await (await wb.render({sheetName:'Как заполнять',range:'A1:B18',scale:1,format:'png'})).arrayBuffer()));
await fs.writeFile(p+'/r2-artifact-authored-text.json',JSON.stringify(edits,null,2));
console.log('AUTHORED_TEXT_CELLS',Object.values(edits).reduce((n,x)=>n+Object.keys(x).length,0));
