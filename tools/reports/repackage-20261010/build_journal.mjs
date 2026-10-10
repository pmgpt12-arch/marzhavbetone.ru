import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const root=process.argv[2];
if(!root)throw new Error('Pass the absolute staging directory containing p4 and journal-source.json');
const raw=await fs.readFile(root+'/journal-source.json','utf8');
const src=JSON.parse(raw); const wb=Workbook.create();
console.log(wb.help('worksheet.pageLayout',{include:'index,examples,notes',maxChars:3500}).ndjson);
const old=await SpreadsheetFile.importXlsx(await FileBlob.load(root+'/p4/35-obshiy-zhurnal-rabot.xlsx'));
const oldView=await old.render({sheetName:'Рабочий журнал',range:'A1:M8',scale:1,format:'png'}).catch(()=>null);
if(oldView)await fs.writeFile(root+'/journal-before.png',new Uint8Array(await oldView.arrayBuffer()));
const col=i=>String.fromCharCode(65+i);
function init(name,n=7){
 const s=wb.worksheets.add(name);s.showGridLines=false;s.tabColor='#262F37';
 const r=s.getRange(`A1:${col(n-1)}160`);r.format.font={name:'Arial',size:10,color:'#262F37'};r.format.verticalAlignment='center';r.format.rowHeight=24;
 s.getRange('A:A').format.columnWidth=6;for(let i=1;i<n;i++)s.getRange(`${col(i)}:${col(i)}`).format.columnWidth=25;
 return s;
}
function merged(s,row,text,n,height=30,bold=false){s.mergeCells(`A${row}:${col(n-1)}${row}`);s.getRange(`A${row}`).values=[[text]];const r=s.getRange(`A${row}:${col(n-1)}${row}`);r.format.wrapText=true;r.format.rowHeight=height;r.format.font={name:'Arial',size:bold?14:10,color:'#262F37',bold};}
function table(s,row,headers,nblank=3,widths){
 const n=headers.length, end=col(n-1);s.getRange(`A${row}:${end}${row}`).values=[headers];
 for(let i=0;i<n;i++)if(widths)s.getRange(`${col(i)}:${col(i)}`).format.columnWidth=widths[i];
 const h=s.getRange(`A${row}:${end}${row}`);h.format={fill:'#F2EFE9',font:{name:'Arial',size:10,bold:true,color:'#262F37'},wrapText:true,verticalAlignment:'center',horizontalAlignment:'center'};
 const estimates=headers.map((v,i)=>Math.ceil(v.length/((widths?.[i]||25)*.95)));
 h.format.rowHeight=Math.max(42,Math.max(...estimates)*13+12);
 s.getRange(`A${row+1}:${end}${row+1}`).values=[Array.from({length:n},(_,i)=>i+1)];s.getRange(`A${row+1}:${end}${row+1}`).format.horizontalAlignment='center';
 const body=s.getRange(`A${row+2}:${end}${row+1+nblank}`);body.values=Array.from({length:nblank},()=>Array(n).fill(null));body.format.rowHeight=48;body.format.wrapText=true;
 s.getRange(`A${row}:${end}${row+1+nblank}`).format.borders={preset:'all',style:'thin',color:'#D9D9D9'};
 return row+2+nblank;
}
const title=init('Титульный лист');let row=2;
merged(title,row++,'Общий журнал работ',7,30,true);
merged(title,row++,'Форма приложения № 1 к приказу Минстроя России от 02.12.2022 № 1026/пр',7,25);
merged(title,row++,'Заполните листы и распечатайте бумажный журнал. До начала ведения журнал брошюруют и нумеруют. Для ведения в электронной форме используется XML по порядку приказа.',7,42);
merged(title,row++,'Источник: https://publication.pravo.gov.ru/Document/View/0001202212300009',7,25);
row++;
let buf=[];
function flush(){if(!buf.length)return;const text=buf.join(' ');merged(title,row++,text,7,Math.max(24,Math.ceil(text.length/140)*15+8));buf=[];}
const label=/^(Застройщик$|Технический заказчик$|Лицо,|Уполномоченный|Сведения о|Общие сведения|Начало |Окончание |В настоящем|В журнале|Регистрационная|Другие лица|М\.П\.|Общий журнал,|№ |по_)/;
for(const [line,text0] of src.filter(x=>x[0]<=456)){
 const text=text0.trim();if(!text)continue;
 if(text.includes(' | ')){
  flush();if(text.startsWith('---')||/^1\s*\|/.test(text)||!text.replace(/[|\s\u00a0]/g,''))continue;
  const headers=text.split('|').map(t=>t.trim());row=table(title,row,headers,2,headers.length===6?[6,24,18,28,54,12]:[6,44,40,40,18]);row++;continue;
 }
 if(/^_/.test(text)){flush();merged(title,row++,text,7,24);continue;}
 if(label.test(text))flush();buf.push(text);
}flush();
for(let i=1;i<=6;i++){
 const start=src.findIndex(x=>x[1]===`### Раздел ${i}`);
 const next=i===6?src.length:src.findIndex(x=>x[1]===`### Раздел ${i+1}`);
 const section=src.slice(start+1,next).map(x=>x[1]).filter(Boolean);
 const heading=section.find(x=>!x.includes('|'));const headers=section.find(x=>x.startsWith('№')).split('|').map(t=>t.trim());
 const s=init(`Раздел ${i}`,headers.length);merged(s,2,`Раздел ${i}`,headers.length,28,true);merged(s,3,heading,headers.length,50);
 const widths={1:[6,35,30,27,24,38],2:[6,33,57,25,40],3:[6,19,25,83,34],4:[6,38,30,23,45,23,45],5:[6,105,55],6:[6,20,55,25,32,25,32]}[i];
 const end=table(s,5,headers,14,widths);s.freezePanes.freezeRows(6);
}
wb.recalculate();
console.log((await wb.inspect({kind:'sheet',include:'id,name',maxChars:1500})).ndjson);
const out=await SpreadsheetFile.exportXlsx(wb);await out.save(root+'/p4/35-obshiy-zhurnal-rabot.xlsx');
for(let i=0;i<7;i++){
 const s=wb.worksheets.getItemAt(i);const p=await wb.render({sheetName:s.name,range:i===0?'A1:G18':`A1:${col(({1:6,2:5,3:5,4:7,5:3,6:7})[i]-1)}10`,scale:1,format:'png'});
 await fs.writeFile(root+`/journal-${i}.png`,new Uint8Array(await p.arrayBuffer()));
}
console.log('EXPORT_OK');
