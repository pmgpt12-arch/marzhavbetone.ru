import fs from 'node:fs/promises';import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const ROOT=process.env.NSP_ROOT;if(!ROOT)throw new Error('NSP_ROOT is required');const routes=JSON.parse(await fs.readFile(ROOT+'/tools/nsp-free-downloads-20261021/routes.json','utf8'));
let proof=[];
for(const [slug,file,start,last] of [['bankrotstvo','02-reestr-priznakov-po-obektu.xlsx',63,'K'],['uderzhaniya','02-reestr-uderzhaniy-po-obektu.xlsx',40,'N']]){
 const route=routes.find(x=>x.slug===slug),input=ROOT+'/products-storage/'+route.folder+'/'+file;await fs.copyFile(input,'/tmp/nsp-free-original/'+route.folder+'--'+file);
 const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(input)),sheet=wb.worksheets.getItemAt(0);
 for(let r=start;r<=start+3;r++){sheet.mergeCells('A'+r+':'+last+r);sheet.getRange('A'+r+':'+last+r).format.wrapText=true;sheet.getRange('A'+r+':'+last+r).format.rowHeight=r===start+1?36:28;}
 sheet.getRange('A'+(start+1)).values=[['Комплект «'+route.product+'» - '+route.rubles.toLocaleString('ru-RU')+' ₽.']];sheet.getRange('A'+(start+2)).values=[[route.product_url]];sheet.getRange('A'+(start+3)).values=[['Вопросы по комплекту: nastoronepodryadchika@yandex.ru']];
 wb.recalculate();
 const range='A'+start+':'+last+(start+3);const png=await wb.render({sheetName:sheet.name,range,scale:1});await fs.writeFile('/tmp/nsp-free-xlsx/'+route.folder+'-after.png',new Uint8Array(await png.arrayBuffer()));
 const inspect=await wb.inspect({kind:'region',sheetId:sheet.name,range,maxChars:1800});
 await (await SpreadsheetFile.exportXlsx(wb)).save('/tmp/nsp-free-xlsx/'+file);proof.push({input,output:'/tmp/nsp-free-xlsx/'+file,range,inspect:inspect.ndjson});
}
await fs.writeFile('/tmp/nsp-free-xlsx/proof.json',JSON.stringify(proof,null,2));console.log('XLSX_CANDIDATES=2');
