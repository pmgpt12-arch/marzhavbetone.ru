import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const dir=fileURLToPath(new URL('.',import.meta.url));
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(`${dir}/print-source.xlsx`));
const s=w.worksheets.getItem('Реестр затрат'),g=w.worksheets.getItem('Как заполнять');
const set=(a,v)=>s.getRange(a).values=[[v]];
set('H1','Не покрыто, ₽');
s.getRange('A2:J52').format.rowHeight=24;
s.getRange('A53:J53').format.rowHeight=22;
g.getRange('A6').values=[['Непокрытая часть, ₽']];
set('C54','Предварительно не покрыто ценой:');
set('C56','Непокрытая сумма / плановая прибыль:');
s.getRange('C53:J53').merge();
s.getRange('C53:J53').format.wrapText=false;
s.getRange('C53').formulas=[['=IF(COUNTBLANK(D2:D52)>0,"Заполните покрытие всех 51 строк; неприменимые отметьте явно",IF(COUNTBLANK(I2:I52)>0,"Заполните статус каждой строки",IF(SUMPRODUCT((I2:I52<>"покрыто, проверено")*(I2:I52<>"принято")*(I2:I52<>"не применяется")*(ISNUMBER(H2:H52)=FALSE))>0,"Есть непокрытые затраты без числовой оценки",IF(SUMPRODUCT(((I2:I52="покрыто, проверено")+(I2:I52="принято"))*(G2:G52=""))>0,"Укажите документы покрытия для закрытых позиций","Проверка заполнена; решение о цене принимает руководитель"))))']];
s.getRange('H54').formulas=[['=SUMIFS(H2:H52,I2:I52,"<>покрыто, проверено",I2:I52,"<>принято",I2:I52,"<>не применяется")']];
s.getRange('H56').formulas=[['=IF(OR(H55="",H55<=0),"",H54/H55)']];
s.getRange('D2:D52').dataValidation={allowBlank:true,errorAlert:{style:'stop',title:'Проверьте значение',message:'Выберите значение из списка; для денежной графы введите число не меньше нуля.'},rule:{type:'list',values:['да','частично','нет','уточнить','не применяется']}};
s.getRange('F2:F52').dataValidation={allowBlank:true,errorAlert:{style:'stop',title:'Проверьте значение',message:'Выберите значение из списка; для денежной графы введите число не меньше нуля.'},rule:{type:'list',values:['подрядчик','генподрядчик','заказчик','не распределено']}};
g.getRange('D1:D8').values=[['Статусы реестра'],['проверить'],['в запросе'],['в протоколе разногласий'],['покрыто, проверено'],['принято'],['не применяется'],['риск принят']];
s.getRange('I2:I52').dataValidation={allowBlank:true,errorAlert:{style:'stop',title:'Проверьте значение',message:'Выберите значение из списка; для денежной графы введите число не меньше нуля.'},rule:{type:'list',formula1:"'Как заполнять'!$D$2:$D$8"}};
s.getRange('H2:H52').dataValidation={allowBlank:true,errorAlert:{style:'stop',title:'Проверьте значение',message:'Выберите значение из списка; для денежной графы введите число не меньше нуля.'},rule:{type:'decimal',operator:'greaterThanOrEqual',formula1:0}};
s.getRange('H55').dataValidation={allowBlank:true,errorAlert:{style:'stop',title:'Проверьте значение',message:'Выберите значение из списка; для денежной графы введите число не меньше нуля.'},rule:{type:'decimal',operator:'greaterThanOrEqual',formula1:0}};
g.getRange('B2:B9').values=[
 ['Укажите «да», «частично», «нет», «уточнить» или «не применяется». Проверяйте покрытие расценкой, ресурсом и начислениями. Все 51 строки требуют отметки.'],
 ['Номер позиции или раздела расчёта, которым расход покрыт полностью либо частично. При отсутствии покрытия оставьте пустым.'],
 ['Укажите подрядчика, генподрядчика, заказчика либо «не распределено»; сошлитесь на договор, проект или письменное решение.'],
 ['Реквизиты документа и пункта о распределении расхода или его покрытии. Для «покрыто, проверено» и «принято» документ обязателен.'],
 ['Введите только оценку непокрытой части расхода на весь объём работ. Ноль означает проверенное отсутствие остатка. Пустая клетка — оценка отсутствует.'],
 ['«проверить», «в запросе», «в протоколе разногласий», «риск принят» входят в предварительный итог. «покрыто, проверено», «принято», «не применяется» исключаются из него. «Риск принят» означает, что компания согласилась нести непокрытый расход.'],
 ['H54 суммирует непокрытую часть с учётом статуса. H55 — плановая прибыль компании по объекту до этих расходов. H56 показывает долю прибыли при положительном H55. Проверяйте сообщение над итогом и незаполненные оценки.'],
 ['Для новой затраты используйте подходящую строку с расшифровкой в комментарии и без повторного счёта. Формулы охватывают строки 2–52. Строки ниже итогов в расчёт не входят. До подписания подтвердите полноту проверки и согласуйте остаток риска.']
];
for(const [i,height] of [38,28,38,38,38,58,48,58].entries()) g.getRange(`A${i+2}:B${i+2}`).format.rowHeight=height;
const log=[];
const val=a=>s.getRange(a).values[0][0];
const check=(name,amount,ratio,warning)=>{w.recalculate();assert.equal(val('H54'),amount,name+' amount');if(ratio!==undefined){if(ratio===null)assert.ok(val('H56')===null||val('H56')==='',name+' ratio blank');else assert.ok(Math.abs(val('H56')-ratio)<1e-8,name+' ratio');}log.push({name,amount:val('H54'),ratio:val('H56'),message:val('C53'),expectedWarning:warning,warningMatches:String(val('C53')).includes(warning)});};
check('blank',0,null,'Заполните покрытие');
s.getRange('D2:D52').values=[['не применяется']];s.getRange('I2:I52').values=[['не применяется']];set('H55',1000000);
check('all nonapplicable',0,0,'Проверка заполнена');
for(const [r,status,h,doc] of [[2,'в запросе',200000,''],[3,'в протоколе разногласий',80000,''],[4,'покрыто, проверено',100000,'Смета п.4'],[5,'принято',50000,'Соглашение'],[6,'риск принят',30000,'Решение директора']]){set('D'+r,'нет');set('I'+r,status);set('H'+r,h);set('G'+r,doc);}
check('coverage and accepted commercial risk',310000,.31,'Проверка заполнена');
set('H2',null);check('missing amount',110000,.11,'без числовой оценки');
set('H2','200 тыс');check('pasted nonnumeric amount',110000,.11,'без числовой оценки');
set('H2',200000);set('G4',null);check('covered without evidence',310000,.31,'документы покрытия');
set('G4','Смета п.4');set('H55',0);check('zero profit',310000,null,'Проверка заполнена');
set('H55',1000000);set('D52','нет');set('I52','в запросе');set('H52',25000);check('last row',335000,.335,'Проверка заполнена');
set('I52','не применяется');check('exclude last row stale amount',310000,.31,'Проверка заполнена');
// Restore the empty buyer form and keep formula-driven outputs.
s.getRange('D2:J52').clear({applyTo:'contents'});set('H55',null);w.recalculate();
const errors=await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:1000});
await fs.writeFile(`${dir}/scenario-report.json`,JSON.stringify({status:'AMOUNT_RATIO_PASS_WARNING_REQUIRES_NATIVE_CHECK',engineLimitation:'Array ISNUMBER in SUMPRODUCT warning is not reliably evaluated by artifact engine; native LibreOffice scenarios are required.',scenarios:log,errorScan:errors.ndjson},null,2));
for(const [name,sheet,range] of [['after-top','Реестр затрат','A1:J9'],['after-bottom','Реестр затрат','C49:J56'],['after-guide','Как заполнять','A1:B9']]){const b=await w.render({sheetName:sheet,range,scale:1.2,format:'png'});await fs.writeFile(`${dir}/${name}.png`,new Uint8Array(await b.arrayBuffer()));}
await (await SpreadsheetFile.exportXlsx(w)).save(`${dir}/authored.xlsx`);
console.log('P13_ARTIFACT_AUTHOR_PASS scenarios='+log.length);
