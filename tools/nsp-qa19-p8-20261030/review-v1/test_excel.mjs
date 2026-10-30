import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const R='/workspace/scratch/1c70cef937ec/qa19-p8';await fs.mkdir(R+'/test-input',{recursive:true});
const f9=(await fs.readdir(R+'/candidate')).find(n=>n.startsWith('09'));
const f2=(await fs.readdir(R+'/candidate')).find(n=>n.startsWith('02'));
let manifest=[];
const base={'Договор и аванс':{B5:12000000,B6:3600000,B8:'генподрядчик отказался от исполнения, о наших нарушениях не заявлено',B11:3600000},'Выполнено':{
 B6:'КС-2',C6:'1 от 01.09.2026',E6:2000000,F6:'подписан обеими сторонами',I6:600000,J6:1400000,
 B7:'КС-2',C7:'2 от 01.10.2026',E7:1500000,F7:'подписан обеими сторонами',I7:450000,J7:950000
}};
const extras={'Выполнено':{B8:'КС-2',C8:'3 от 15.10.2026',E8:1100000,F8:'передан, не подписан',G8:46310,H8:'Опись и ЭДО',I8:0,J8:0},'Встречное':{B6:'материалы и оборудование остались на объекте',C6:'Материалы по накладной',D6:480000,E6:'Накладная 12',F6:'да'}};
const merge=(...sets)=>{const o={};for(const s of sets)for(const [n,v]of Object.entries(s))o[n]={...o[n],...v};return o;};
const cases=[
 ['09-blank',{},null],['09-accepted-only',base,2450000],
 ['09-full-example',merge(base,extras),870000],
 ['09-missing-cash',merge(base,{'Выполнено':{J7:null}}),null],
 ['09-overallocated',merge(base,{'Выполнено':{I6:2000001}}),null],
 ['09-negative-input',merge(base,{'Договор и аванс':{B6:-1}}),null],
 ['09-last-row',merge(base,{'Выполнено':{B45:'КС-2',C45:'Последний акт',E45:500000,F45:'подписан обеими сторонами',I45:0,J45:0}}),1950000],
 ['09-creditor',merge(base,{'Выполнено':{E7:5000000}}),-1050000]
];
for(const [id,changes,expected] of cases){
 const w=await SpreadsheetFile.importXlsx(await FileBlob.load(R+'/candidate/'+f9));
 for(const [n,cs]of Object.entries(changes))for(const [a,v]of Object.entries(cs))w.worksheets.getItem(n).getRange(a).values=[[v]];
 w.recalculate();const value=w.worksheets.getItem('Сальдо').getRange('B32').values[0][0];
 const out=await SpreadsheetFile.exportXlsx(w);await out.save(R+'/test-input/'+id+'.xlsx');
 manifest.push({id,sheet:'Сальдо',cell:'B32',expected,artifactValue:value});
}
const conditions={B5:1000000,B6:0,B7:0,B8:'пропорционально из каждой КС',B9:0,B10:0,B11:0,B12:0,B13:0,B14:0,B15:0,B16:1,B17:1,B18:80,B19:0,B20:0};
for(const [id,override,expected]of [['02-delay',{},800000],['02-invalid-percent',{B6:101},null]]){
 const w=await SpreadsheetFile.importXlsx(await FileBlob.load(R+'/candidate/'+f2));const s=w.worksheets.getItem('Условия');
 for(const [a,v]of Object.entries({...conditions,...override}))s.getRange(a).values=[[v]];
 w.worksheets.getItem('График КС').getRange('B5').values=[[100]];
 for(let r=6;r<=40;r++)w.worksheets.getItem('График КС').getRange('B'+r).values=[[0]];
 w.recalculate();const value=w.worksheets.getItem('Сравнение').getRange('B7').values[0][0];
 const out=await SpreadsheetFile.exportXlsx(w);await out.save(R+'/test-input/'+id+'.xlsx');
 manifest.push({id,sheet:'Сравнение',cell:'B7',expected,artifactValue:value});
}
await fs.writeFile(R+'/internal/EXCEL_TEST_CASES.json',JSON.stringify(manifest,null,2));console.log('Created',manifest.length,'scenarios');
