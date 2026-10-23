import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const base=new URL('.',import.meta.url).pathname;
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(base+'source/02-reestr-izyatiy-po-obektu.xlsx'));
const s=w.worksheets.getItem('Изъятия'),g=w.worksheets.getItem('Как считать');
const put=(sh,cell,value)=>sh.getRange(cell).values=[[value]];
put(s,'A1','Деньги и обязательства по объекту');
put(s,'A2','Дата среза');put(s,'D2',null);put(s,'E2','Пусто — не проверено. Ноль — проверено, отсутствует.');
s.getRange('A3:G3').values=[['Показатель','Основание','Что проверить','Сумма, ₽','Условия и документы','За чей счёт','Сверка и исключение повторов']];
const details=[
 ['Аванс — непогашенный остаток',null,'Выдано минус зачтено и возвращено',null,'По расчётам и документам сторон','—','Отдельное обязательство; не сумма изъятых денег'],
 ['Гарантийное удержание',null,'Фактический остаток удержания на дату',null,'База, процент, событие и срок возврата','Подрядчик','Не повторять в денежном обеспечении'],
 ['Вознаграждение банка',null,'Фактически уплаченные комиссии',null,'С учётом подтверждённых возвратов','По договору','Номинал гарантии сюда не включать'],
 ['Денежное покрытие в банке',null,'Только фактически заблокированные деньги',null,'Условия освобождения по соглашению с банком','По соглашению','Залог имущества и лимит гарантии не включать'],
 ['Обеспечительный платёж',null,'Переданные и не возвращённые деньги',null,'Условия возврата по договору','По договору','Не повторять сумму удержания из строки 5'],
 ['Генподрядные услуги',null,'Оплачено или документально списано',null,'Акты, расчёты, платежи и заявления','По договору','Без повторов и с учётом возвратов'],
 ['Штрафы и иные списания',null,'Фактически уменьшившие расчёты суммы',null,'Основание, документ и позиция по спору','—','Не включать повторно суммы других строк'],
 ['Выполнено, но не принято',null,'Стоимость подтверждённых работ',null,'Документы выполнения и сдачи, причины отказа','—','Может включать удержание; с ним не складывать']
];
s.getRange('A4:G11').values=details;
const aggregate=(refs)=>'=IF(OR(NOT(ISNUMBER($D$2)),$D$2<1),"УКАЖИТЕ ДАТУ",IF(COUNT('+refs+')<>'+refs.split(',').length+',"НЕ ПРОВЕРЕНО",IF(MIN('+refs+')<0,"ОШИБКА: сумма меньше нуля",ROUND(SUM('+refs+'),2))))';
const direct=(ref)=>'=IF(OR(NOT(ISNUMBER($D$2)),$D$2<1),"УКАЖИТЕ ДАТУ",IF(NOT(ISNUMBER('+ref+')),"НЕ ПРОВЕРЕНО",IF('+ref+'<0,"ОШИБКА: сумма меньше нуля",ROUND('+ref+',2))))';
const outputs=[
 [12,'Удержано и заблокировано',aggregate('D5,D7,D8'),'Сумма строк 5, 7 и 8. Только непересекающиеся денежные остатки.'],
 [13,'Фактические затраты',aggregate('D6,D9'),'Сумма строк 6 и 9. Не прибавляется к остаткам для оценки кассы.'],
 [14,'Непогашенный аванс',direct('D4'),'Строка 4. Не показывает доступный остаток денег на счёте.'],
 [15,'Выполнено, но не принято',direct('D11'),'Строка 11. Срок оплаты и наличие долга проверяются отдельно.'],
 [16,'Штрафы и иные списания',direct('D10'),'Строка 10. Спорность и отсутствие повторов подтверждаются документами.']
];
for(const [row,label,formula,note]of outputs){put(s,'A'+row,label);s.getRange('D'+row).formulas=[[formula]];put(s,'E'+row,note);}
put(s,'A18','Общий кассовый разрыв здесь не рассчитывается. Для него нужны доступные деньги и календарь поступлений и выплат.');
put(s,'A19','Суммы не складываются между показателями. Сверку оснований и исключение повторов фиксируйте в графе G.');
put(g,'A1','Как заполнить реестр');g.getRange('A2:C2').clear({applyTo:'all'});
g.getRange('A3:C3').values=[['Шаг','Действие','Правило']];
g.getRange('A4:C14').values=[
 [1,'Укажите дату среза в ячейке D2 первого листа.','Все остатки и накопленные затраты относятся к одной дате.'],
 [2,'Заполните сумму каждой строки.','Пусто означает «не проверено». После проверки введите число, в том числе 0 при отсутствии суммы. Отрицательные и нечисловые значения не дают корректного итога.'],
 [3,'Аванс укажите отдельным остатком.','Выданный аванс минус зачтённые и возвращённые суммы. Наличие обязательства не означает, что эти деньги недоступны на счёте.'],
 [4,'Удержание берите из сверенных расчётов.','База и процент определяются договором. Не умножайте процент автоматически на сумму чистого платежа. Учитывайте возвраты.'],
 [5,'В покрытие банка включайте только деньги.','Имущественный залог и номинал гарантии не являются заблокированными денежными средствами. Условия освобождения проверьте в банковском соглашении.'],
 [6,'Разделите расходы и возвратные остатки.','Комиссии банка и оплаченные либо списанные услуги — затраты. Удержание, денежное покрытие и обеспечительный платёж — отдельные остатки.'],
 [7,'Исключите повторение одной суммы.','Одно удержание нельзя одновременно внести как обеспечительный платёж. Укажите основания и сверку в графе G; автоматически выявить такие повторы по суммам невозможно.'],
 [8,'Непринятые работы и списания проверяйте отдельно.','Стоимость работ может уже включать удержание. Не прибавляйте её к сумме удержания. Не учитывайте один платёж повторно в строках расходов и списаний.'],
 [9,'Читайте каждый итог отдельно.','Здесь нет общего итога «денег не у вас», чистого долга или расчёта запаса ликвидности. Достоверность оснований подтверждается документами.'],
 [10,'Для финансирования составьте календарь.','Сопоставьте доступный остаток денег, ожидаемые поступления, сроки зачёта аванса и обязательные выплаты по датам.'],
 [11,'Пересчитывайте после новых событий.','Платёж, зачёт аванса, возврат покрытия и акт меняют разные показатели. Сохраните датированную копию и документы сверки.']
];
// Retain the source's two worksheets and seven-column register; resize only the affected content.
for(const [sh,range]of [[s,'A1:G19'],[g,'A1:C14']]){
 sh.getRange(range).format.font={name:'Arial',size:11,color:'#222222',bold:false,italic:false};
 sh.getRange(range).format.fill='#FFFFFF';sh.getRange(range).format.verticalAlignment='center';
 sh.getRange(range).format.borders={preset:'none'};sh.getRange(range).format.wrapText=true;
 sh.getRange('A1').format.font={name:'Arial',size:15,bold:true,italic:false,color:'#222222'};sh.getRange('A1').format.wrapText=false;sh.showGridLines=false;
 sh.getRange('A1').format.rowHeight=28;
}
for(const [col,width]of [['A',34],['B',13],['C',34],['D',24],['E',39],['F',17],['G',34]])s.getRange(col+'1:'+col+'19').format.columnWidth=width;
s.getRange('A2:G2').format.rowHeight=42;s.getRange('A3:G3').format.rowHeight=35;s.getRange('A4:G11').format.rowHeight=48;s.getRange('A12:G16').format.rowHeight=45;
s.getRange('A3:G3').format.fill='#343B40';s.getRange('A3:G3').format.font={bold:true,color:'#FFFFFF'};
s.getRange('D4:D11').format.fill='#FFF2CC';s.getRange('D2').format.fill='#FFF2CC';
s.getRange('D4:D16').setNumberFormat('#,##0.00');s.getRange('D2').setNumberFormat('dd.mm.yyyy');
s.getRange('D4:D16').format.horizontalAlignment='right';s.getRange('A12:D16').format.font.bold=true;
s.getRange('A12:D16').format.fill='#F3F0E8';
for(const row of [18,19]){s.getRange('A'+row).format.wrapText=false;s.getRange('A'+row).format.font={size:10,italic:true};s.getRange('A'+row).format.rowHeight=23;}
g.getRange('A1:A14').format.columnWidth=7;g.getRange('B1:B14').format.columnWidth=42;g.getRange('C1:C14').format.columnWidth=56;
g.getRange('A3:C3').format.fill='#343B40';g.getRange('A3:C3').format.font={bold:true,color:'#FFFFFF'};
g.getRange('A3:C3').format.rowHeight=28;g.getRange('A4:C14').format.rowHeight=60;
g.getRange('A1').format.wrapText=false;
w.recalculate();
const serial=Math.round((Date.UTC(2026,9,23)-Date.UTC(1899,11,30))/86400000);
const zeros=()=>Object.fromEntries([4,5,6,7,8,9,10,11].map(n=>['D'+n,0]));
const cases=[
 {name:'missing-date',inputs:{},expected:['УКАЖИТЕ ДАТУ','УКАЖИТЕ ДАТУ','УКАЖИТЕ ДАТУ','УКАЖИТЕ ДАТУ','УКАЖИТЕ ДАТУ']},
 {name:'verified-zero',inputs:{D2:serial,...zeros()},expected:[0,0,0,0,0]},
 {name:'advance-only',inputs:{D2:serial,...zeros(),D4:1000000},expected:[0,0,1000000,0,0]},
 {name:'separate-categories',inputs:{D2:serial,D4:600000,D5:10000,D6:2000,D7:50000,D8:20000,D9:3000,D10:4000,D11:100000},expected:[80000,5000,600000,100000,4000]},
 {name:'missing-held-only',inputs:{D2:serial,...zeros(),D5:null},expected:['НЕ ПРОВЕРЕНО',0,0,0,0]},
 {name:'negative-held',inputs:{D2:serial,...zeros(),D5:-1},expected:['ОШИБКА: сумма меньше нуля',0,0,0,0]},
 {name:'text-fee',inputs:{D2:serial,...zeros(),D6:'ошибка'},expected:[0,'НЕ ПРОВЕРЕНО',0,0,0]},
 {name:'boolean-advance',inputs:{D2:serial,...zeros(),D4:true},expected:[0,0,'НЕ ПРОВЕРЕНО',0,0]},
 {name:'work-includes-retention',inputs:{D2:serial,...zeros(),D5:10000,D11:100000},expected:[10000,0,0,100000,0]},
 {name:'offset-is-separate',inputs:{D2:serial,...zeros(),D10:25000},expected:[0,0,0,0,25000]},
 {name:'money-decimals',inputs:{D2:serial,...zeros(),D5:10000.25,D7:50000.5,D8:20000.3},expected:[80001.05,0,0,0,0]},
 {name:'invalid-date',inputs:{D2:-1,...zeros()},expected:['УКАЖИТЕ ДАТУ','УКАЖИТЕ ДАТУ','УКАЖИТЕ ДАТУ','УКАЖИТЕ ДАТУ','УКАЖИТЕ ДАТУ']}
];
const results=[];
for(const c of cases){s.getRange('D2').values=[[null]];s.getRange('D4:D11').values=Array.from({length:8},()=>[null]);for(const [cell,v]of Object.entries(c.inputs))put(s,cell,v);w.recalculate();const actual=s.getRange('D12:D16').values.flat();assert.deepEqual(actual,c.expected,c.name);results.push({...c,actual,status:'PASS_ARTIFACT_ENGINE'});}
s.getRange('D2').values=[[null]];s.getRange('D4:D11').values=Array.from({length:8},()=>[null]);w.recalculate();
await fs.writeFile(base+'proof/XLSX_CASES.json',JSON.stringify({date_serial:serial,engine:'artifact-tool; native Office pending',cases:results},null,2));
await fs.writeFile(base+'proof/XLSX_FORMULAS.json',JSON.stringify(outputs.map(([row,label,formula])=>({cell:'D'+row,label,formula})),null,2));
for(const [sh,range,name]of [[s,'A1:G19','register'],[g,'A1:C14','guide']]){const b=await w.render({sheetName:sh.name,range,scale:1,format:'png'});await fs.writeFile(base+'proof/after-'+name+'.png',new Uint8Array(await b.arrayBuffer()));}
await(await SpreadsheetFile.exportXlsx(w)).save(base+'output/02-reestr-izyatiy-po-obektu.xlsx');
console.log('AUTHORED_XLSX',results.length,'SCENARIOS',results.length*5,'EXPECTATIONS');
