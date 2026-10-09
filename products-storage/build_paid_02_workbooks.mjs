import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';

const source=process.argv[2];
const output=process.argv[3];
if(!source || !output) throw new Error('Usage: node build_workbooks.mjs <source-dir> <output-dir>');
await fs.mkdir(output,{recursive:true});
const graphite='#263039',white='#FFFFFF',gold='#8E6F32',light='#F3F0E8';

for(const name of ['07-raschet-stoimosti.xlsx','08-zhurnal-doprabot.xlsx']){
 const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(`${source}/${name}`));
 const sheet=wb.worksheets.getItem('Реестр');
 const instruction=wb.worksheets.getItem('Инструкция');
 const last=name.startsWith('07')?'J':'L';
 sheet.showGridLines=false;
 sheet.freezePanes.freezeRows(3);
 sheet.getRange(`A1:${last}1`).format.fill=white;
 sheet.getRange(`A1:${last}1`).format.font={name:'Arial',size:16,bold:true,color:graphite};
 sheet.getRange(`A3:${last}3`).format.fill=graphite;
 sheet.getRange(`A3:${last}3`).format.font={name:'Arial',size:10,bold:true,color:white};
 sheet.getRange(`A3:${last}3`).format.rowHeight=26;
 sheet.getRange(`A4:${last}104`).format.font={name:'Arial',size:10,color:graphite};
 sheet.getRange(`A4:${last}104`).format.rowHeight=23;
 sheet.getRange(`A4:${last}104`).format.verticalAlignment='center';
 sheet.getRange(`A4:${last}103`).format.borders={insideHorizontal:{style:'thin',color:'#E1E3E4'}};
 sheet.getRange('A2').format.font={name:'Arial',size:10,italic:true,color:graphite};
 instruction.getRange('A1').format.font={name:'Arial',size:15,bold:true,color:graphite};
 instruction.showGridLines=false;

 if(name.startsWith('07')){
  sheet.getRange('A2').values=[['Заполните работу, единицу, объём, цену и её источник. Коэффициент пустой = 1. Итог считайте по заполненным строкам.']];
  sheet.getRange('B4:E103').format.fill=light;
  sheet.getRange('G4:H103').format.fill=light;
  sheet.getRange('J4:J103').format.fill=light;
  sheet.getRange('F4').formulas=[['=IF(OR(D4="",E4=""),"",D4*E4)']];
  sheet.getRange('F4:F103').fillDown();
  sheet.getRange('I4').formulas=[['=IF(F4="","",F4*IF(H4="",1,H4))']];
  sheet.getRange('I4:I103').fillDown();
  sheet.getRange('E4:F104').setNumberFormat('#,##0.00');
  sheet.getRange('I4:I104').setNumberFormat('#,##0.00');
  sheet.getRange('D4:D103').setNumberFormat('#,##0.000');
  sheet.getRange('H4:H103').setNumberFormat('0.000');
  sheet.getRange('H104').values=[['Итого']];
  sheet.getRange('F104').formulas=[['=SUM(F4:F103)']];
  sheet.getRange('I104').formulas=[['=SUM(I4:I103)']];
  sheet.getRange('F104:I104').format.font={name:'Arial',size:10,bold:true,color:graphite};
  sheet.getRange('H104:I104').format.fill='#E9DFCA';
  instruction.getRange('A3').values=[['Одна строка — одна работа или ресурс. Укажите единицу, количество, цену и источник цены (номер документа, дата, поставщик). Коэффициент вводите числом: 1,15 означает +15%; пустое поле равно 1. Сумма и итог считаются автоматически; незаполненные количество или цена оставляют результат пустым. Сверьте объёмы с формой 02, приложите расчёт к соглашению 11 и сохраните копию по объекту.']];
  // Boundary check in memory, then restore the blank buyer input.
  sheet.getRange('D4:E4').values=[[2,100]];
  sheet.getRange('H4').values=[[1.2]];
  wb.recalculate();
  console.log(name,'test',JSON.stringify({F4:sheet.getRange('F4').values,I4:sheet.getRange('I4').values}));
  sheet.getRange('D4:E4').clear({applyTo:'contents'});
  sheet.getRange('H4').clear({applyTo:'contents'});
 }else{
  sheet.getRange('A2').values=[['Одна работа — одна строка. Записывайте основание, решение по объёму, факт, закрытие и оплату с подтверждающими документами.']];
  sheet.getRange('A4:G103').format.fill=light;
  sheet.getRange('H4:L103').format.fill=white;
  sheet.getRange('B4:B103').setNumberFormat('dd.mm.yyyy');
  sheet.getRange('G4:G103').setNumberFormat('#,##0.00');
  sheet.getRange('H4:H103').dataValidation={rule:{type:'list',values:['К согласованию','Согласовано','Не согласовано']}};
  sheet.getRange('I4:I103').dataValidation={rule:{type:'list',values:['Не начато','В работе','Выполнено']}};
  sheet.getRange('K4:L103').dataValidation={rule:{type:'list',values:['Нет','Да']}};
  instruction.getRange('A3').values=[['Одна строка — одна дополнительная работа. Запишите дату обнаружения, инициатора, место и основание, единицу и объём, стоимость по расчёту 07. Укажите статус согласования и выполнения отдельно; ссылки на форму 02, акт 04, фото 09, КС-2 и платёжный документ внесите в соответствующие поля. «Да» в колонке «Оплачено» ставьте по фактическому поступлению, а не по подписанию соглашения. Сохраняйте копию журнала для каждого объекта и проверяйте записи при каждом изменении.']];
 }
 wb.recalculate();
 console.log(name,'key',(await wb.inspect({kind:'table',sheetId:sheet.sheetId,range:name.startsWith('07')?'D3:I5':'G3:L5',maxChars:1200,tableMaxRows:3,tableMaxCols:8})).ndjson);
 const err=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:10},maxChars:1200});
 console.log(name,'errors',err.ndjson);
 const preview=await wb.render({sheetName:'Реестр',range:name.startsWith('07')?'A1:J8':'A1:L8',scale:1.5,format:'png'});
 await fs.writeFile(`${output}/${name}.png`,new Uint8Array(await preview.arrayBuffer()));
 const how=await wb.render({sheetName:'Инструкция',range:'A1:A3',scale:1.5,format:'png'});
 await fs.writeFile(`${output}/${name}.instruction.png`,new Uint8Array(await how.arrayBuffer()));
 const file=await SpreadsheetFile.exportXlsx(wb);
 await file.save(`${output}/${name}`);
}
