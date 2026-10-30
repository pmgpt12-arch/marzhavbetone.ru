import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const R='/workspace/scratch/1c70cef937ec/qa19-p8';
const outputDir='/workspace/scratch/1c70cef937ec/outputs/p8-20261030';
await fs.mkdir(outputDir,{recursive:true});
const f=(await fs.readdir(R+'/source')).find(n=>n.startsWith('09'));
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(R+'/source/'+f));
const edits={
 'Пример заполнения':{
  A17:'Гарантийное удержание отдельно не добавляется',
  B17:'0,00 — повторное включение в этом примере исключено',
  B22:'1 100 000 + 480 000 + 100 000 = 1 680 000,00',
  B23:'870 000,00 к возврату при обоснованности спорных позиций',
  A25:'Без неподписанного акта и материалов остаток по двусторонним актам 2 450 000 руб. Спорные 1 580 000 руб. раскрывайте отдельно. Удержание, уже включённое в неоплаченный остаток акта, повторно не добавляйте.'
 },
 'Договор и аванс':{A18:'Доля аванса без погашения по двусторонним актам'},
 'Сальдо':{
  A32:'Сальдо по введённым работам и встречным суммам',
  C32:'Арифметический результат с заявленными спорными позициями. Основание, срок возврата и допустимость учёта каждой суммы проверьте отдельно по карте 11.',
  C24:'Проверьте срок и основание возврата. Не включайте сумму повторно, если она уже находится в неоплаченном остатке актов.',
  A44:'Отделите согласованные и спорные суммы в карте 11 и ответе 10. Сальдо по введённым данным не подтверждает само по себе наступление обязанности возврата.'
 },
 'Как читать':{A26:'Основной маршрут: алгоритм 08, карта проверки 11, расчёт 09, ответ 10. Отдельно проверьте основание требования и срок возврата. Материалы и удержания не учитывайте дважды.'}
};
for(const [name,cells]of Object.entries(edits)){
 const s=w.worksheets.getItem(name);
 for(const [address,value]of Object.entries(cells))s.getRange(address).values=[[value]];
}
w.worksheets.getItem('Как читать').getRange('A19').format.rowHeight=42;
w.worksheets.getItem('Как читать').getRange('A26').format.rowHeight=58;
w.worksheets.getItem('Сальдо').getRange('B37:B42').format.wrapText=true;
w.worksheets.getItem('Сальдо').getRange('A37:C42').format.rowHeight=70;
w.recalculate();
const results={};
for(const name of ['Сальдо','Пример заполнения']){
 results[name]=(await w.inspect({kind:'region',sheetId:name,range:name==='Сальдо'?'A29:C34':'A16:C25',maxChars:3000,tableMaxCellChars:130})).ndjson;
 const p=await w.render({sheetName:name,range:name==='Сальдо'?'A29:C34':'A15:C25',scale:1.5,format:'png'});
 await fs.writeFile(R+'/internal/excel-after-'+(name==='Сальдо'?'saldo':'example')+'.png',new Uint8Array(await p.arrayBuffer()));
}
const out=await SpreadsheetFile.exportXlsx(w);await out.save(outputDir+'/'+f);
await fs.copyFile(outputDir+'/'+f,R+'/candidate/'+f);
await fs.writeFile(R+'/internal/EXCEL_EDIT_RECEIPT.json',JSON.stringify({edits,inspection:results},null,2));
console.log('Exported scoped edits');
