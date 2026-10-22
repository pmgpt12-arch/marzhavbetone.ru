import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
async function main(){
const source=process.argv[2],output=process.argv[3];
if(!source||!output)throw Error('Usage: bundled-node build.mjs <source-dir> <output-dir>');
await fs.mkdir(output,{recursive:true});
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(source+'/07-raschet-stoimosti.xlsx'));
const wb8=await SpreadsheetFile.importXlsx(await FileBlob.load(source+'/08-zhurnal-doprabot.xlsx'));
const before8=await wb8.render({sheetName:'Реестр',range:'A1:L8',scale:1.5,format:'png'});
await fs.writeFile(output+'/before8.png',new Uint8Array(await before8.arrayBuffer()));
const s=wb.worksheets.getItem('Реестр');
const numeric=['D','E','H'];
s.getRange('F4').formulas=[['=IF(OR(ISBLANK(D4),ISBLANK(E4)),"",D4*E4)']];s.getRange('F4:F103').fillDown();
s.getRange('I4').formulas=[['=IF(OR(ISBLANK(D4),ISBLANK(E4)),"",F4*IF(ISBLANK(H4),1,H4))']];s.getRange('I4:I103').fillDown();
for(const col of numeric) s.getRange(`${col}4:${col}103`).conditionalFormats.addCustom(`=AND(${col}4<>"",NOT(ISNUMBER(${col}4)))`,{fill:'#FCE8E6',font:{color:'#9C2020',bold:true}});
const s8=wb8.worksheets.getItem('Реестр');
for(const [range,values] of [['H4:H103',['К согласованию','Согласовано','Не согласовано']],['I4:I103',['Не начато','В работе','Выполнено']],['K4:L103',['Нет','Да']]]){
 s8.getRange(range).dataValidation=null;
 s8.getRange(range).dataValidation={rule:{type:'list',values},errorAlert:{style:'stop',title:'Выберите статус',message:'Выберите значение из списка статусов.'}};
 for(const col of range==='K4:L103'?['K','L']:[range[0]]) s8.getRange(`${col}4:${col}103`).conditionalFormats.addCustom(`=AND(${col}4<>"",${values.map(v=>`${col}4<>"${v}"`).join(',')})`,{fill:'#FCE8E6',font:{color:'#9C2020',bold:true}});
}
const results=[];
for(const [name,q,price,k,expected] of [['positive',2.5,200,1.15,575],['blank_coefficient',2.5,200,null,500],['zero',0,200,1.15,0],['zero_coefficient',2,200,0,0],['blank_quantity',null,200,1.15,''],['negative_preserved',-2,200,1,-400]]){
 for(const [col,val] of [['D',q],['E',price],['H',k]])s.getRange(col+'4').values=[[val]];
 wb.recalculate();const actual=s.getRange('I4').values[0][0];
 results.push({name,actual,expected,pass:actual===expected});
 if(actual!==expected)throw Error(name+':'+JSON.stringify(actual));
}
s.getRange('D4').values=[['abc']];s.getRange('E4').values=[[200]];wb.recalculate();
const invalid=await wb.render({sheetName:'Реестр',range:'A1:J6',scale:1.5,format:'png'});
await fs.writeFile(output+'/invalid-input.png',new Uint8Array(await invalid.arrayBuffer()));
for(const col of numeric)s.getRange(col+'4').values=[[null]];
for(const [col,val]of [['D',3],['E',100],['H',2]])s.getRange(col+'103').values=[[val]];
wb.recalculate();if(s.getRange('I104').values[0][0]!==600)throw Error('row103 not included in total');
results.push({name:'last_input_row_103',actual:600,expected:600,pass:true});
for(const col of numeric)s.getRange(col+'103').values=[[null]];
wb.recalculate();wb8.recalculate();
for(const [name,book,last]of [['07-raschet-stoimosti.xlsx',wb,'J'],['08-zhurnal-doprabot.xlsx',wb8,'L']]){
 const pic=await book.render({sheetName:'Реестр',range:`A1:${last}8`,scale:1.5,format:'png'});
 await fs.writeFile(output+'/'+name+'.png',new Uint8Array(await pic.arrayBuffer()));
 await(await SpreadsheetFile.exportXlsx(book)).save(output+'/'+name);
}
await fs.writeFile(output+'/calculation-checks.json',JSON.stringify({engine:'artifact-tool',cases:results,not_native_excel:true,negative_semantics:'preserved existing calculation; subject approval remains open'},null,2));
const fixture=await SpreadsheetFile.importXlsx(await FileBlob.load(output+'/07-raschet-stoimosti.xlsx'));
const fsheet=fixture.worksheets.getItem('Реестр');
const fixtures=[['positive',2.5,200,1.15,575],['blank_coefficient',2.5,200,null,500],['zero_quantity',0,200,1.15,0],['zero_coefficient',2,200,0,0],['blank_quantity',null,200,1.15,''],['negative',-2,200,1,-400],['invalid_text','abc',200,1,'#VALUE!']];
for(let i=0;i<fixtures.length;i++){const [name,d,e,h]=fixtures[i];const r=i+4;fsheet.getRange('B'+r).values=[[name]];for(const [c,v]of [['D',d],['E',e],['H',h]])fsheet.getRange(c+r).values=[[v]];}
fixture.recalculate();await(await SpreadsheetFile.exportXlsx(fixture)).save(output+'/native-fixture.xlsx');
await fs.writeFile(output+'/native-expectations.json',JSON.stringify(fixtures.map((x,i)=>({cell:'I'+(i+4),scenario:x[0],expected:x[4]})),null,2));
console.log('EXPORTED; artifact-tool cases:',JSON.stringify(results));
}
main().catch(e=>{console.error('CONTROLLED_ERROR:',e.message);process.exitCode=1;});
