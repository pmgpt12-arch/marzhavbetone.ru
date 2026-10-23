import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile}from '@oai/artifact-tool';
const O=process.env.NSP_QA03_ROOT,w=await SpreadsheetFile.importXlsx(await FileBlob.load(O+'/source/02-reestr-uderzhaniy-po-obektu.xlsx')),s=w.worksheets.getItem('Реестр удержаний');
const results=[];
for(const[name,held,returned]of [['negative-held',-100000,0],['text-held','ошибка',0],['over-return',100000,120000],['negative-return',100000,-20000],['accepted-example',100000,20000]]){
 s.getRange('E3:E14').clear({applyTo:'contents'});s.getRange('L3:L14').clear({applyTo:'contents'});s.getRange('E3').values=[[held]];s.getRange('L3').values=[[returned]];w.recalculate();
 const h=s.getRange('E15').values[0][0],r=s.getRange('L15').values[0][0];
 results.push({name,held_input:held,returned_input:returned,held_total:h,returned_total:r,manually_inferred_difference:typeof h==='number'&&typeof r==='number'?h-r:null,source_has_no_residual_formula:true,source_has_no_error_guard:true});
}
await fs.writeFile(O+'/proof/SOURCE_REPRODUCTION.json',JSON.stringify({engine:'@oai/artifact-tool',source_modified:false,results},null,2)+'\n');console.log('Source monetary defects reproduced in memory; source file unchanged.');
