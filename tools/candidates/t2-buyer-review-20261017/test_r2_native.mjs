import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const p=fileURLToPath(new URL('.',import.meta.url));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(p+'/final-files/03-opis-peredavaemogo-komplekta.xlsx'));
const sh=wb.worksheets.getItem('Опись');
sh.getRange('B11:H14').values=[
 ['акт освидетельствования скрытых работ','Армирование плиты','№12 от 14.04.2026','акт №4 от 30.04.2026',2,2,'оригинал'],
 ['исполнительная схема','Колонны 1 этажа','СХ-07 от 16.04.2026','акт №4 от 30.04.2026',1,2,'оригинал'],
 ['документ о качестве материала (паспорт, сертификат)','Бетон B25','паспорт №218','акт №4 от 30.04.2026',1,2,'копия заверенная'],
 ['реестр, опись, титульный лист','Титульный лист тома 3','—',null,1,2,'оригинал']
];
await fs.mkdir('/tmp/t2-author-0267/native-inputs',{recursive:true});
wb.recalculate();
console.log('VALID',(await wb.inspect({kind:'table',range:'Опись!C132:E133',include:'values,formulas',maxChars:1800})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save('/tmp/t2-author-0267/native-inputs/valid.xlsx');
sh.getRange('F11').values=[[null]];
wb.recalculate();
console.log('MISSING',(await wb.inspect({kind:'table',range:'Опись!C132:E133',include:'values,formulas',maxChars:1800})).ndjson);
await (await SpreadsheetFile.exportXlsx(wb)).save('/tmp/t2-author-0267/native-inputs/missing.xlsx');
