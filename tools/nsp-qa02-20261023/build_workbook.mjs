import fs from 'node:fs/promises';
import {Workbook,FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const O='/workspace/scratch/4c2f1716d70e/qa02-repo/tools/nsp-qa02-20261023';
const MAIN='Калькулятор срока оплаты';
const dateOK=x=>`IF(ISNUMBER(${x}),AND(${x}>=DATE(2016,8,1),${x}<=DATE(2100,12,31),MOD(${x},1)=0),FALSE)`;
const moneyOK=x=>`IF(ISNUMBER(${x}),AND(${x}>=0,ROUND(${x},2)=${x}),FALSE)`;
const rateOK=x=>`IF(ISNUMBER(${x}),${x}>=0,FALSE)`;
const m=x=>`'${MAIN}'!$${x[0]}$${x.slice(1)}`;
const sn=d=>(Date.parse(d+'T00:00:00Z')-Date.UTC(1899,11,30))/86400000;
const holidays=['2026-01-01','2026-01-02','2026-01-03','2026-01-04','2026-01-05','2026-01-06','2026-01-07','2026-01-08','2026-01-09','2026-02-23','2026-03-08','2026-03-09','2026-05-01','2026-05-09','2026-05-11','2026-06-12','2026-11-04','2026-12-31'];
const annual=r=>`IF(D${r}="",${m('B15')},D${r})`;
const daily=r=>`IF(E${r}="",${m('B10')},E${r})`;
const val=(s,a,v)=>s.getRange(a).values=[[v]];
const formula=(s,a,f)=>s.getRange(a).formulas=[['='+f]];

export async function build(){
 const w=await SpreadsheetFile.importXlsx(await FileBlob.load(O+'/source/02-kalkulyator-sroka-oplaty.xlsx'));
 const s=w.worksheets.getItemAt(0),p=w.worksheets.add('Периоды'),pay=w.worksheets.add('Платежи'),cal=w.worksheets.add('Календарь');
 s.getRange('A1:C32').clear({applyTo:'all'});
 const rows=[
 ['Параметр','Значение','Как заполнить'],
 ['Дата КС-2',null,'Справочно. Срок определяет событие в строке 6.'],
 ['Дата КС-3',null,'Справочно. Не складывайте КС-2 и накопительную КС-3.'],
 ['Срок оплаты, дней',null,'Целое число от 0. День события не входит.'],
 ['Тип срока','календарные','рабочие / календарные / дата'],
 ['Дата договорного события',null,'Укажите подтверждённое событие, предусмотренное договором.'],
 ['Крайний день оплаты',null,'Перенос на рабочий день включён для календаря 2026.'],
 ['Календарных дней просрочки',null,'С первого дня после срока по дату расчёта включительно.'],
 ['Дата окончания расчёта',null,'Фиксированная дата. TODAY() не используется.'],
 ['Договорная пеня, % в день',null,'Введите 0,1% как 0,1%. Не годовая ставка.'],
 ['Сумма обязательства, руб.',null,'Основной долг до внесённых оплат, без санкций.'],
 ['Выбранная санкция, руб.',null,'Только один режим из строки 13.'],
 ['Режим расчёта',null,'395 / пеня / без санкций. Одновременного начисления нет.'],
 ['Есть неустойка за это нарушение',null,'да / нет / неизвестно. Учитывайте закон и договор.'],
 ['Ставка 395, % годовых',null,'На каждый период проверьте ставку Банка России.'],
 ['Крайняя дата проверена',null,'да — проверены договор, календарь и применимость ст. 193.'],
 ['Основание и ставки проверены',null,'да — проверены выбранная санкция, база и все её периоды.'],
 ['Крайняя дата вручную',null,'Для типа «дата»: окончательная дата после правовой проверки.'],
 ['Исходные данные',null,'Платежи: до 20 строк, только отнесённая на основной долг сумма.'],
 ['Остаток основного долга',null,'Оплаты по дату расчёта включительно вычитаются один раз.'],
 ['Учтено оплат',null,'Будущие оплаты не уменьшают текущий остаток.'],
 ['Оплаты после даты расчёта',null,'Показаны отдельно, в расчёт текущего периода не входят.'],
 ['Проценты по ст. 395',null,'В режиме пени не начисляются. Без капитализации.'],
 ['Договорная пеня',null,'Простая дневная пеня на остаток. Иные модели — отдельный расчёт.'],
 ['Долг и выбранная санкция',null,'Это две разные составляющие. Перенесите их в письмо раздельно.'],
 ['Первый день просрочки',null,'Следующий день после подтверждённого срока оплаты.'],
 ['Периоды и основание',null,'Если ошибка — числовой итог санкции не выдаётся.'],
 ['Как разделить периоды',null,'Новая строка: день изменения ставки или день после частичной оплаты.'],
 ['Дата фактической оплаты',null,'В платеже укажите дату исполнения обязательства и подтверждение банка.'],
 ['Границы модели',null,'Рубли, периоды с 01.08.2016, 20 оплат и 20 периодов. Особые режимы — отдельно.'],
 ['Связь',null,'nastoronepodryadchika@yandex.ru; тема ДЕНЬГИ, файл, лист, ячейка.'],
 ['Порядок работы',null,'Сначала инструкция 01, затем платежи/периоды, список 03 и письмо 04.']
 ];s.getRange('A1:C32').values=rows;
 const hol="'Календарь'!$A$5:$A$22";
 const termOK='IF(ISNUMBER(B4),AND(B4>=0,B4<=366,MOD(B4,1)=0),FALSE)';
 const raw=`IF(B5="рабочие",WORKDAY(B6,B4,${hol}),B6+B4)`;
 const shifted=`WORKDAY((${raw})-1,1,${hol})`;
 formula(s,'B7',`IF(B16<>"да","ПОДТВЕРДИТЕ ДАТУ",IF(B5="дата",IF(${dateOK('B18')},B18,"УКАЖИТЕ ДАТУ"),IF(AND(B5<>"рабочие",B5<>"календарные"),"ТИП СРОКА",IF(NOT(${dateOK('B6')}),"ДАТА СОБЫТИЯ",IF(NOT(${termOK}),"ЦЕЛЫЕ ДНИ 0–366",IF(YEAR(B6)<>2026,"НУЖНА РУЧНАЯ ДАТА",IF(YEAR(${shifted})<>2026,"НУЖНА РУЧНАЯ ДАТА",${shifted})))))))`);
 formula(s,'B8',`IF(AND(ISNUMBER(B7),${dateOK('B9')}),MAX(0,B9-B7),"ПРОВЕРЬТЕ ДАТЫ")`);
 formula(s,'B19',`IF(NOT(ISNUMBER(B7)),"ПРОВЕРЬТЕ СРОК",IF(NOT(${dateOK('B9')}),"ДАТА РАСЧЁТА",IF(NOT(${moneyOK('B11')}),"СУММА ДОЛГА",IF(SUM('Платежи'!$F$5:$F$24)>0,"ПРОВЕРЬТЕ ПЛАТЕЖИ","ГОТОВО"))))`);
 formula(s,'B21',`IF(B19<>"ГОТОВО",B19,SUMIFS('Платежи'!$B$5:$B$24,'Платежи'!$A$5:$A$24,"<="&B9))`);
 formula(s,'B22',`IF(B19<>"ГОТОВО",B19,SUMIFS('Платежи'!$B$5:$B$24,'Платежи'!$A$5:$A$24,">"&B9))`);
 formula(s,'B20',`IF(B19<>"ГОТОВО",B19,IF(B21>B11,"ОПЛАТЫ БОЛЬШЕ ДОЛГА",ROUND(B11-B21,2)))`);
 formula(s,'B26','IF(ISNUMBER(B7),B7+1,"ПРОВЕРЬТЕ СРОК")');
 formula(s,'B27',`IF(B19<>"ГОТОВО",B19,IF(AND(B13<>"проценты 395",B13<>"пеня",B13<>"без санкций"),"ВЫБЕРИТЕ РЕЖИМ",IF(B13="без санкций","НЕ ТРЕБУЮТСЯ",IF(B17<>"да","ПОДТВЕРДИТЕ ОСНОВАНИЕ",IF(OR(AND(B13="проценты 395",B14<>"нет"),AND(B13="пеня",B14<>"да")),"ПРОВЕРЬТЕ НЕУСТОЙКУ",IF(B9<=B7,"ПРОСРОЧКИ НЕТ",IF(SUM('Периоды'!$M$5:$M$24)>0,"ПРОВЕРЬТЕ ПЕРИОДЫ",IF(SUM('Периоды'!$F$5:$F$24)<>B8,"НЕПОЛНОЕ ПОКРЫТИЕ","ГОТОВО"))))))))`);
 formula(s,'B23',`IF(B13<>"проценты 395","НЕ ВЫБРАНО",IF(B27="ГОТОВО",ROUND(SUM('Периоды'!$J$5:$J$24),2),IF(B27="ПРОСРОЧКИ НЕТ",0,B27)))`);
 formula(s,'B24',`IF(B13<>"пеня","НЕ ВЫБРАНО",IF(B27="ГОТОВО",ROUND(SUM('Периоды'!$K$5:$K$24),2),IF(B27="ПРОСРОЧКИ НЕТ",0,B27)))`);
 formula(s,'B12','IF(B13="проценты 395",B23,IF(B13="пеня",B24,IF(B13="без санкций",0,"ВЫБЕРИТЕ РЕЖИМ")))');
 formula(s,'B25','IF(AND(ISNUMBER(B20),ISNUMBER(B12)),SUM(B20,B12),"ПРОВЕРЬТЕ ВВОД")');
 for(const [cell,values]of [['B5',['рабочие','календарные','дата']],['B13',['проценты 395','пеня','без санкций']],['B14',['да','нет','неизвестно']],['B16',['да','нет']],['B17',['да','нет']]])s.getRange(cell).dataValidation={rule:{type:'list',values}};
 s.dataValidations.add({range:'B4',rule:{type:'whole',operator:'between',formula1:0,formula2:366}});

 val(pay,'A1','Платежи по одному обязательству');val(pay,'A2','Только суммы, отнесённые на основной долг. Подтвердите распределение платежа.');
 pay.getRange('A4:F4').values=[['Дата исполнения','Основной долг, руб.','Документ и назначение','Учёт на дату расчёта','Контроль ввода','Ошибок']];
 for(let r=5;r<=24;r++){
  formula(pay,'E'+r,`IF(AND(A${r}="",B${r}="",C${r}=""),"",IF(NOT(${dateOK('A'+r)}),"ОШИБКА: дата",IF(NOT(${moneyOK('B'+r)}),"ОШИБКА: сумма",IF(C${r}="","ОШИБКА: документ","ГОТОВО"))))`);
  formula(pay,'F'+r,`IF(OR(E${r}="",E${r}="ГОТОВО"),0,1)`);
  formula(pay,'D'+r,`IF(E${r}="","",IF(E${r}<>"ГОТОВО",E${r},IF(NOT(${dateOK(m('B9'))}),"НЕТ ДАТЫ РАСЧЁТА",IF(A${r}<=${m('B9')},"УЧТЁН","ПОСЛЕ ДАТЫ"))))`);
 }
 val(pay,'A26','Одна операция — одна строка. Повторный платёж не вносите дважды.');
 val(pay,'A27','По п. 48 Пленума № 7 день оплаты входит в расчёт; база уменьшается со следующего дня.');
 val(pay,'A28','Для другого порядка по специальной норме или договору нужен отдельный расчёт.');

 val(p,'A1','Начисления по периодам');val(p,'A2','Вводите новые начала в A6:A24 по возрастанию. D/E пусто — ставка из главного листа.');
 val(p,'A3','Частичная оплата внутри строки блокирует итог: добавьте начало следующего дня. Новая ставка — с даты её действия.');
 p.getRange('A4:M4').values=[['Начало','Конец','База, руб.','395, % год.','Пеня, %/день','Дней','Дней 1-го года','Полных лет','Дней посл. года','Проценты 395, руб.','Пеня, руб.','Контроль периода','Ошибок']];
 for(let r=5;r<=24;r++){
  const a='A'+r,b='B'+r,c='C'+r;
  if(r===5)formula(p,a,`IF(ISNUMBER(${m('B26')}),${m('B26')},"")`);
  formula(p,b,`IF(AND(${dateOK(a)},${dateOK(m('B9'))}),${r<24?`IF(ISNUMBER(A${r+1}),MIN(A${r+1}-1,${m('B9')}),${m('B9')})`:m('B9')},"")`);
  formula(p,c,`IF(AND(${dateOK(a)},${m('B19')}="ГОТОВО"),${m('B11')}-SUMIFS('Платежи'!$B$5:$B$24,'Платежи'!$A$5:$A$24,"<"&${a}),"")`);
  const order=r>5?`IF(NOT(ISNUMBER(A${r-1})),"ОШИБКА: пропуск строки",IF(${a}<=A${r-1},"ОШИБКА: порядок",ORDER_OK))`:'ORDER_OK';
  const tail=`IF(${b}<${a},"ОШИБКА: границы",IF(${c}<0,"ОШИБКА: переплата",IF(COUNTIFS('Платежи'!$A$5:$A$24,">="&${a},'Платежи'!$A$5:$A$24,"<"&${b})>0,"ОШИБКА: разделите после оплаты",IF(AND(${m('B13')}="проценты 395",NOT(${rateOK(annual(r))})),"ОШИБКА: ставка 395",IF(AND(${m('B13')}="пеня",NOT(${rateOK(daily(r))})),"ОШИБКА: ставка пени","ГОТОВО")))))`;
  const afterorder=order.replace('ORDER_OK',tail);
  formula(p,'L'+r,`IF(AND(${a}="",D${r}="",E${r}=""),"",IF(NOT(${dateOK(a)}),"ОШИБКА: дата",IF(${m('B19')}<>"ГОТОВО","ОШИБКА: входные данные",IF(${a}>${m('B9')},"НЕ УЧТЁН",IF(${a}<${m('B26')},"ОШИБКА: начало до просрочки",${afterorder})))))`);
  formula(p,'M'+r,`IF(OR(L${r}="",L${r}="ГОТОВО",L${r}="НЕ УЧТЁН"),0,1)`);
  formula(p,'F'+r,`IF(L${r}="ГОТОВО",${b}-${a}+1,"")`);
  formula(p,'G'+r,`IF(L${r}="ГОТОВО",MIN(${b},DATE(YEAR(${a})+1,1,1)-1)-${a}+1,"")`);
  formula(p,'H'+r,`IF(L${r}="ГОТОВО",MAX(0,YEAR(${b})-YEAR(${a})-1),"")`);
  formula(p,'I'+r,`IF(L${r}="ГОТОВО",IF(YEAR(${b})>YEAR(${a}),${b}-DATE(YEAR(${b}),1,1)+1,0),"")`);
  formula(p,'J'+r,`IF(AND(L${r}="ГОТОВО",${m('B13')}="проценты 395"),${c}*${annual(r)}*(G${r}/(DATE(YEAR(${a})+1,1,1)-DATE(YEAR(${a}),1,1))+H${r}+I${r}/(DATE(YEAR(${b})+1,1,1)-DATE(YEAR(${b}),1,1))),"")`);
  formula(p,'K'+r,`IF(AND(L${r}="ГОТОВО",${m('B13')}="пеня"),${c}*${daily(r)}*F${r},"")`);
 }
 val(p,'A26','Годовая ставка вводится как 14%, дневная — как 0,1%. Ноль допустим; текст и отрицательная выбранная ставка блокируют итог.');
 val(p,'A27','395: дни делятся на 365/366 по соответствующему календарному году; внутри периода учитываются полные промежуточные годы.');
 val(p,'A28','Начисления складываются без округления по дням/строкам. Итог округляется до копеек на главном листе.');
 val(p,'A29','20 периодов и 20 оплат — предел готового макета. Не вводите дополнительные строки за его пределами.');
 val(p,'A30','Работает для обычного рублёвого долга без капитализации. Лимиты пени, моратории, особая база или иной день начала — отдельная модель.');

 val(cal,'A1','Календарь срока оплаты 2026');val(cal,'A2','Пятидневка 2026. Иной календарь — ручная дата.');
 cal.getRange('A4:C4').values=[['Нерабочая дата','Основание','Источники и условия']];
 holidays.forEach((d,i)=>{val(cal,'A'+(i+5),sn(d));val(cal,'B'+(i+5),['2026-01-09','2026-12-31'].includes(d)?'ПП РФ № 1466':'ТК РФ ст. 112 и перенос');});
 const links=[['ТК РФ ст. 112','https://www.consultant.ru/document/cons_doc_LAW_34683/98ef2900507766e70ff29c0b9d8e2353ea80a1cf/'],['ПП РФ № 1466','https://www.consultant.ru/document/cons_doc_LAW_515170/'],['ГК РФ ст. 191','https://www.consultant.ru/document/cons_doc_LAW_5142/60f6af8755cda8e568604f21cd44e823c3407d8f/'],['ГК РФ ст. 193','https://www.consultant.ru/document/cons_doc_LAW_5142/8aaa310a192d916fce0327f6226a59ffe5b49b9b/'],['Ключевая ставка Банка России','https://www.cbr.ru/hd_base/keyrate/']];
 links.forEach(([t,url],i)=>val(cal,'C'+(i+5),t));
 await fs.writeFile(O+'/proof/XLSX_HYPERLINKS.json',JSON.stringify(links.map(([label,url],i)=>({sheet:'Календарь',cell:'C'+(i+5),label,url})),null,2));
 val(cal,'C11','Автоматический срок — только внутри 2026 года.');val(cal,'C13','Для иных лет используйте проверенную конечную дату.');
 val(cal,'C15','Не переносите день начала просрочки автоматически на рабочий: после срока считаются календарные дни.');
 val(cal,'C18','В строке 16 главного листа подтвердите применимость календаря к вашему обязательству.');
 val(cal,'C21','Ставки не загружаются из сети. Проверяйте все даты изменений по источнику.');

 for(const sh of [s,p,pay,cal]){
  sh.showGridLines=false;const used=sh.getUsedRange();used.format.font={name:'Arial',size:10,color:'#252A30'};used.format.verticalAlignment='center';used.format.rowHeight=22;
  sh.getRange(sh===s?'A1:C1':sh===p?'A4:M4':sh===pay?'A4:F4':'A4:C4').format={fill:'#252A30',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true};
 }
 s.getRange('A:A').format.columnWidth=34;s.getRange('B:B').format.columnWidth=27;s.getRange('C:C').format.columnWidth=54;
 s.getRange('A1:C32').format.wrapText=true;s.getRange('A1:C32').format.rowHeight=25;
 for(const a of ['B2:B6','B9:B11','B13:B18'])s.getRange(a).format.fill='#FFF2CC';
 for(const r of [7,8,12,19,20,21,22,23,24,25,26,27])s.getRange('B'+r).format.fill='#F2F3F5';
 for(const r of [2,3,6,7,9,18,26])s.getRange('B'+r).setNumberFormat('dd.mm.yyyy');
 for(const r of [10,15])s.getRange('B'+r).setNumberFormat('0.00%');
 for(const r of [11,12,20,21,22,23,24,25])s.getRange('B'+r).setNumberFormat('#,##0.00');
 s.getRange('B19:B27').format.font.bold=true;
 s.getRange('A30:C32').format.font.size=9;
 const widths=[15,15,18,12,12,8,10,9,10,18,18,32,8];widths.forEach((v,i)=>p.getRange(String.fromCharCode(65+i)+':'+String.fromCharCode(65+i)).format.columnWidth=v);
 p.getRange('A4:M4').format.rowHeight=48;p.getRange('A5:B24').setNumberFormat('dd.mm.yyyy');p.getRange('D5:E24').setNumberFormat('0.00%');
 p.getRange('C5:C24').setNumberFormat('#,##0.00');p.getRange('J5:K24').setNumberFormat('#,##0.00');p.getRange('L5:L24').format.wrapText=true;p.getRange('A5:L24').format.rowHeight=28;
 p.getRange('A6:A24').format.fill='#FFF2CC';p.getRange('D5:E24').format.fill='#FFF2CC';p.freezePanes.freezeRows(4);
 [15,20,46,23,29,8].forEach((v,i)=>pay.getRange(String.fromCharCode(65+i)+':'+String.fromCharCode(65+i)).format.columnWidth=v);
 pay.getRange('A4:F4').format.rowHeight=36;pay.getRange('A5:A24').setNumberFormat('dd.mm.yyyy');pay.getRange('B5:B24').setNumberFormat('#,##0.00');pay.getRange('A5:C24').format.fill='#FFF2CC';pay.getRange('C5:E24').format.wrapText=true;pay.getRange('A5:F24').format.rowHeight=28;
 cal.getRange('A:A').format.columnWidth=17;cal.getRange('B:B').format.columnWidth=28;cal.getRange('C:C').format.columnWidth=44;cal.getRange('A5:A22').setNumberFormat('dd.mm.yyyy');cal.getRange('C5:C22').format.wrapText=true;cal.getRange('A5:C22').format.rowHeight=28;
 for(const r of [15,18,21])cal.getRange('A'+r+':C'+r).format.rowHeight=46;
 s.tabColor='#252A30';
 return w;
}
export const inputs={main:MAIN,cells:['B2','B3','B4','B5','B6','B9','B10','B11','B13','B14','B15','B16','B17','B18']};
export function reset(w){const s=w.worksheets.getItem(MAIN);for(const c of inputs.cells)val(s,c,null);val(s,'B5','календарные');const p=w.worksheets.getItem('Периоды');p.getRange('A6:A24').clear({applyTo:'contents'});p.getRange('D5:E24').clear({applyTo:'contents'});w.worksheets.getItem('Платежи').getRange('A5:C24').clear({applyTo:'contents'});}
export function apply(w,values){for(const [sheet,cells]of Object.entries(values)){const s=w.worksheets.getItem(sheet);for(const [cell,v]of Object.entries(cells))val(s,cell,v);}}
if(process.argv[1]?.endsWith('build_workbook.mjs')){
 const w=await build();w.recalculate();await fs.mkdir(O+'/candidate',{recursive:true});await fs.mkdir(O+'/proof',{recursive:true});
 console.log((await w.inspect({kind:'sheet',include:'id,name',maxChars:1500})).ndjson);
 const x=await SpreadsheetFile.exportXlsx(w);await x.save(O+'/candidate/02-kalkulyator-sroka-oplaty.xlsx');
 for(const name of [MAIN,'Периоды','Платежи','Календарь']){const p=await w.render({sheetName:name,range:name===MAIN?'A1:C32':name==='Периоды'?'A1:M30':name==='Платежи'?'A1:F28':'A1:C22',scale:1.3,format:'png'});await fs.writeFile(O+'/proof/'+name+'.png',new Uint8Array(await p.arrayBuffer()));}
 await fs.writeFile(O+'/proof/ARTIFACT_INSPECT.json',JSON.stringify(await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#N/A',options:{useRegex:true,maxResults:30},maxChars:3000}),null,2));
 console.log('EXPORTED_CANDIDATE');
}
