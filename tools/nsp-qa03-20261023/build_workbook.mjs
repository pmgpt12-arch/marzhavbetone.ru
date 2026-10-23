import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile}from '@oai/artifact-tool';
export const O=process.env.NSP_QA03_ROOT;if(!O)throw Error('NSP_QA03_ROOT required');
export const MAIN='Реестр удержаний',TERMS='Условия возврата';
const money=x=>`IF(ISNUMBER(${x}),AND(${x}>=0,ROUND(${x},2)=${x}),FALSE)`;
const date=x=>`IF(ISNUMBER(${x}),AND(${x}>=1,${x}<=2958465,MOD(${x},1)=0),FALSE)`;
const term=(c,r)=>`'${TERMS}'!${c}${r}`;
const val=(s,a,v)=>s.getRange(a).values=[[v]];
const formula=(s,a,f)=>s.getRange(a).formulas=[['='+f]];
function merged(s,a,text){s.getRange(a).merge();val(s,a.split(':')[0],text);}
export async function build(){
 const w=Workbook.create();const s=w.worksheets.add(MAIN),t=w.worksheets.add(TERMS);
 merged(s,'A1:I1','Гарантийное удержание по объекту');
 merged(s,'A2:I2','Остаток удержания и сумма к возврату проверяются раздельно. Все суммы в рублях.');
 val(s,'A3','На:');merged(s,'C3:I3','Сверяйте суммы, даты погашений и условия возврата на эту дату.');
 s.getRange('C4:I4').values=[['Сумма актов','Удержано всего','Возвращено деньгами','Иное погашение','Остаток удержания','К возврату на дату','Актов в реестре']];
 merged(s,'A6:I6','Заполняйте светлые поля. G:I — формулы. Подтверждения и сроки — на листе «Условия возврата».');
 s.getRange('A8:I8').values=[['№','Акт номер и дата','Сумма акта','Удержано до погашений','Возвращено деньгами','Иное погашение','Остаток','К возврату на дату','Готовность к возврату']];
 merged(t,'A1:M1','Условия и подтверждения возврата');
 merged(t,'A2:M2','Строки соответствуют тем же актам на первом листе. Перепишите условие дословно; подтвердите событие, срок и документы.');
 merged(t,'A3:M3','J — дата последнего денежного возврата, M — дата иного подтверждённого погашения. В K укажите документы и распределение сумм.');
 merged(t,'A4:M4','Крайний день G вводится после проверки договора и календаря. Сам реестр не назначает универсальный срок возврата.');
 merged(t,'A6:M6','При первичном требовании оставьте F пустой: срок ещё не запущен. После доставки внесите F и проверенную дату G.');
 t.getRange('A8:M8').values=[['№','Пункт удержания и возврата','Событие и документ','Дата события','Возврат','Доставлено требование','Крайний день возврата','Срок и его основание','Условия: да/нет/спор','Денежный возврат дата','Подтверждения сумм','Письма ответы и примечания','Иное погашение дата']];
 for(let r=9;r<=20;r++){
  val(s,'A'+r,r-8);val(t,'A'+r,r-8);
  const active=`COUNTA(B${r}:F${r})+COUNTA(${term('B',r)}:${term('M',r)})`;
  const cash=`AND(${date(term('J',r))},${term('J',r)}<=$B$3,${term('K',r)}<>"")`;
  const other=`AND(${date(term('M',r))},${term('M',r)}<=$B$3,${term('K',r)}<>"")`;
  formula(s,'G'+r,`IF(${active}=0,"",IF(NOT(${date('$B$3')}),"ДАТА РАСЧЁТА",IF(OR(B${r}="",LEN(TRIM(B${r}&""))=0),"УКАЖИТЕ АКТ",IF(COUNTIFS($B$9:$B$20,B${r})>1,"ПОВТОР АКТА",IF(NOT(AND(${['C','D','E','F'].map(c=>money(c+r)).join(',')})),"ПРОВЕРЬТЕ СУММЫ",IF(D${r}>C${r},"УДЕРЖАНО > АКТА",IF(SUM(E${r}:F${r})>D${r},"ПОГАШЕНО > УДЕРЖАНО",IF(AND(E${r}>0,NOT(${cash})),"ВОЗВРАТ: ДАННЫЕ",IF(AND(F${r}>0,NOT(${other})),"ПОГАШЕНИЕ: ДАННЫЕ",ROUND(D${r}-SUM(E${r}:F${r}),2))))))))))`);
  const c=col=>term(col,r);
  const dueOK=`AND(${date(c('G'))},${c('G')}>=${c('D')},IF(${c('E')}="по требованию",${c('G')}>=${c('F')},TRUE))`;
  formula(s,'I'+r,`IF(AND(ISTEXT(G${r}),G${r}=""),"",IF(NOT(ISNUMBER(G${r})),G${r},IF(G${r}=0,IF(D${r}=0,"УДЕРЖАНИЯ НЕТ","ПОГАШЕНО ПОЛНОСТЬЮ"),IF(${c('I')}="нет","УСЛОВИЯ НЕ ВЫПОЛНЕНЫ",IF(${c('I')}="спор","СПОРНЫЕ УСЛОВИЯ",IF(${c('I')}<>"да","ПОДТВЕРДИТЕ УСЛОВИЯ",IF(OR(${c('B')}="",${c('C')}="",${c('H')}=""),"ОСНОВАНИЕ И СРОК",IF(NOT(AND(${date(c('D'))},${c('D')}<=$B$3)),"ПОДТВЕРДИТЕ СОБЫТИЕ",IF(AND(${c('E')}<>"автоматически",${c('E')}<>"по требованию"),"ВИД ВОЗВРАТА",IF(AND(${c('E')}="по требованию",${c('F')}=""),"НАПРАВЬТЕ ТРЕБОВАНИЕ",IF(AND(${c('E')}="по требованию",NOT(AND(${date(c('F'))},${c('F')}<=$B$3))),"ПОДТВЕРДИТЕ ДОСТАВКУ",IF(NOT(${dueOK}),"ПОДТВЕРДИТЕ СРОК",IF(${c('G')}>$B$3,"СРОК НЕ НАСТУПИЛ","К ВОЗВРАТУ")))))))))))))`);
  formula(s,'H'+r,`IF(AND(ISTEXT(G${r}),G${r}=""),"",IF(NOT(ISNUMBER(G${r})),G${r},IF(OR(I${r}="К ВОЗВРАТУ",G${r}=0),G${r},IF(OR(I${r}="СРОК НЕ НАСТУПИЛ",I${r}="УСЛОВИЯ НЕ ВЫПОЛНЕНЫ"),0,I${r}))))`);
 }
 const empty='COUNTBLANK($G$9:$G$20)=12',valid='COUNT($G$9:$G$20)+COUNTBLANK($G$9:$G$20)=12';
 for(const c of ['C','D','E','F','G'])formula(s,c+'5',`IF(${empty},"НЕТ ДАННЫХ",IF(NOT(${valid}),"ПРОВЕРЬТЕ РЕЕСТР",SUM(${c}9:${c}20)))`);
 formula(s,'H5',`IF(${empty},"НЕТ ДАННЫХ",IF(COUNT($H$9:$H$20)+COUNTBLANK($H$9:$H$20)<>12,"ПРОВЕРЬТЕ УСЛОВИЯ",SUM(H9:H20)))`);
 formula(s,'I5',`IF(${empty},"НЕТ ДАННЫХ",12-COUNTBLANK(G9:G20))`);
 const notes=[
 'D — удержано до возвратов; E — денежные возвраты; F — иное подтверждённое погашение. Каждая операция учитывается один раз.',
 'Не включайте одну операцию одновременно в E и F. Спорные списания не принимаются автоматически как погашение.',
 'Остаток G не равен сумме к возврату H при ненаступившем или неподтверждённом сроке. При споре проверьте условия.',
 'До 12 актов. Порядок, пример и письмо — файлы 01 и 04. Поддержка: nastoronepodryadchika@yandex.ru.'
 ];notes.forEach((x,i)=>merged(s,`A${22+i}:I${22+i}`,x));
 const legal=JSON.parse(await fs.readFile(O+'/LEGAL_SOURCES.json','utf8')).sources;
 const links=['327.1','314','165.1','410','411'].map((key,i)=>({sheet:TERMS,cell:'B'+(22+i),label:legal[key].title,url:legal[key].url}));
 links.forEach((x,i)=>{val(t,'A'+(22+i),i+1);merged(t,`B${22+i}:M${22+i}`,x.label);});
 await fs.writeFile(O+'/proof/XLSX_HYPERLINKS.json',JSON.stringify(links,null,2)+'\n');
 for(const sh of [s,t]){
  sh.showGridLines=false;sh.tabColor='#252A30';sh.getUsedRange().format.font={name:'Arial',size:11,color:'#252A30'};sh.getUsedRange().format.verticalAlignment='center';sh.getUsedRange().format.rowHeight=22;
  sh.getRange(sh===s?'A1:I1':'A1:M1').format.font={name:'Arial',size:15,bold:true,color:'#000000'};
  sh.getRange(sh===s?'A8:I8':'A8:M8').format={fill:'#252A30',font:{name:'Arial',size:10.5,bold:true,color:'#FFFFFF'},wrapText:true};
  sh.getRange(sh===s?'A1:I25':'A1:M26').format.wrapText=true;sh.freezePanes.freezeRows(8);
 }
 [4,22,15,16,16,16,16,17,27].forEach((x,i)=>s.getRange(String.fromCharCode(65+i)+':'+String.fromCharCode(65+i)).format.columnWidth=x);
 [4,18,24,13,17,14,14,20,13,14,24,22,14].forEach((x,i)=>t.getRange(String.fromCharCode(65+i)+':'+String.fromCharCode(65+i)).format.columnWidth=x);
 s.getRange('B3').format.fill='#FFF2CC';s.getRange('B3').setNumberFormat('dd.mm.yyyy');s.getRange('B9:F20').format.fill='#FFF2CC';s.getRange('C9:H20').setNumberFormat('#,##0.00');
 s.getRange('G9:I20').format.fill='#F2F3F5';s.getRange('C5:I5').format.fill='#F2F3F5';s.getRange('C5:H5').setNumberFormat('#,##0.00');s.getRange('C5:I5').format.font.bold=true;
 t.getRange('B9:M20').format.fill='#FFF2CC';for(const c of ['D','F','G','J','M'])t.getRange(c+'9:'+c+'20').setNumberFormat('dd.mm.yyyy');
 for(const[c,values]of [['E',['автоматически','по требованию']],['I',['да','нет','спор']]])t.getRange(c+'9:'+c+'20').dataValidation={rule:{type:'list',values}};
 s.getRange('A1:I1').format.rowHeight=24;s.getRange('A2:I2').format.rowHeight=18;s.getRange('A3:I3').format.rowHeight=22;s.getRange('A4:I4').format.rowHeight=32;s.getRange('A5:I5').format.rowHeight=28;s.getRange('A6:I6').format.rowHeight=18;s.getRange('A7:I7').format.rowHeight=4;s.getRange('A8:I8').format.rowHeight=40;s.getRange('A9:I20').format.rowHeight=24;s.getRange('A21:I21').format.rowHeight=6;s.getRange('A22:I25').format.rowHeight=22;s.getRange('A22:I25').format.font.size=10;
 t.getRange('A1:M1').format.rowHeight=24;t.getRange('A5:M5').format.rowHeight=4;t.getRange('A7:M7').format.rowHeight=4;t.getRange('A8:M8').format.rowHeight=52;t.getRange('A9:M20').format.rowHeight=44;t.getRange('A21:M21').format.rowHeight=6;t.getRange('A22:M26').format.rowHeight=20;t.getRange('B22:M26').format.font.color='#72552B';
 return w;
}
export function reset(w){const s=w.worksheets.getItem(MAIN),t=w.worksheets.getItem(TERMS);s.getRange('B3').values=[[null]];s.getRange('B9:F20').clear({applyTo:'contents'});t.getRange('B9:M20').clear({applyTo:'contents'});}
export function apply(w,inputs){for(const[name,cells]of Object.entries(inputs)){const s=w.worksheets.getItem(name);for(const[a,v]of Object.entries(cells))val(s,a,v);}}
if(process.argv[1]?.endsWith('build_workbook.mjs')){
 const w=await build();w.recalculate();const x=await SpreadsheetFile.exportXlsx(w);await x.save(O+'/candidate/02-reestr-uderzhaniy-po-obektu.xlsx');
 for(const[sheet,range]of [[MAIN,'A1:I25'],[TERMS,'A1:M26']]){const b=await w.render({sheetName:sheet,range,scale:1.1,format:'png'});await fs.writeFile(O+'/proof/'+(sheet===MAIN?'candidate-main':'candidate-terms')+'.png',new Uint8Array(await b.arrayBuffer()));}
 console.log('Workbook candidate exported; no new sheet protection (source was unprotected).');
}
