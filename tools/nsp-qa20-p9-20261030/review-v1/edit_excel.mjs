import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const R='/workspace/scratch/1c70cef937ec/qa20-p9';const outputDir='/workspace/scratch/1c70cef937ec/outputs/p9-20261030';await fs.mkdir(outputDir,{recursive:true});await fs.mkdir(R+'/test-input',{recursive:true});
const f=(await fs.readdir(R+'/source')).find(n=>n.endsWith('.xlsx'));const w=await SpreadsheetFile.importXlsx(await FileBlob.load(R+'/source/'+f));const s=w.worksheets.getItem('Объект и должник');
s.getRange('B27').formulas=[['=IFERROR(IF(OR(B14="",B15="",B17="",B18="",B23="",B24="",B25=""),"НЕ ЗАПОЛНЕНО: процедура, даты, публикация, норма и проверяющий",IF(OR(NOT(ISNUMBER(B14)),NOT(ISNUMBER(B17)),NOT(ISNUMBER(B24)),B14<=0,B17<=0,B24<=0,B14<>INT(B14),B17<>INT(B17),B24<>INT(B24)),"ОШИБКА: даты должны быть датами Excel без времени",IF(NOT(OR(B15="наблюдение",B15="внешнее управление",B15="конкурсное производство")),"ПРОВЕРЬТЕ: процедура требует отдельного порядка",IF(B24<B17,"ОШИБКА: предельная дата раньше публикации",IF(B24<TODAY(),"Указанная предельная дата истекла: откройте файл 09","Дней до указанной предельной даты: "&(B24-TODAY())))))),"ОШИБКА: проверьте исходные даты")']];
s.getRange('B27:C27').format.wrapText=true;s.getRange('A27:C27').format.rowHeight=50;
s.getRange('A14').format.wrapText=true;s.getRange('A14:C14').format.rowHeight=42;
s.getRange('A24').format.wrapText=true;
const example=w.worksheets.getItem('Пример заполнения');example.getRange('A5:A11').format.wrapText=true;example.getRange('A5:M11').format.rowHeight=32;
example.getRange('A16:M16').format.rowHeight=44;
w.worksheets.getItem('Реестр документов').getRange('A3:M3').format.rowHeight=44;
s.getRange('C24').values=[['Предельная дата по применимой норме. Внутреннюю контрольную дату назначьте отдельно раньше неё. Excel не устанавливает юридически верную дату.']];s.getRange('A24:C24').format.rowHeight=55;
w.worksheets.getItem('Итоги').getRange('A16').values=[['Основной долг и санкции сведите отдельно в расчёт 10. Он заполняется вручную. Суммы значений документов не равны задолженности. Сверьте итог с заявлением 08 и описью 05.']];
w.worksheets.getItem('Итоги').getRange('A16:C16').format.rowHeight=55;
w.recalculate();let out=await SpreadsheetFile.exportXlsx(w);await out.save(outputDir+'/'+f);
const changes={B14:46000,B15:'наблюдение',B17:46100,B18:'Официальная публикация номер дата URL',B23:'Статья 71 с проверкой процедуры',B24:50000,B25:'Проверил Иванов дата'};
let tests=[];
for(const [id,override,prefix]of [['valid',{},'Дней до'],['missing-rule',{B23:null},'НЕ ЗАПОЛНЕНО'],['text-date',{B24:'завтра'},'ОШИБКА'],['before-publication',{B24:46001},'ОШИБКА'],['missing-source',{B18:null},'НЕ ЗАПОЛНЕНО'],['expired',{B24:46200},'Указанная предельная дата истекла']]){
 for(const [a,v]of Object.entries({...changes,...override}))s.getRange(a).values=[[v]];
 w.recalculate();const actual=s.getRange('B27').values[0][0];if(!String(actual).startsWith(prefix))throw new Error(id+': '+actual);
 out=await SpreadsheetFile.exportXlsx(w);await out.save(R+'/test-input/'+id+'.xlsx');tests.push({id,expectedPrefix:prefix,artifactValue:actual});
}
await fs.writeFile(R+'/internal/EXCEL_TEST_CASES.json',JSON.stringify(tests,null,2));console.log('Six input cases passed Artifact Tool');
