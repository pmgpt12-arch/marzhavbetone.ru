import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root='/workspace/scratch/6ca5fc64b5d2/next-qa/';
const plans=await fs.readdir(root+'plans');const cases=JSON.parse(await fs.readFile(root+'regression-cases.json','utf8'));let results=[];
for(const name of plans.sort()){
const p=JSON.parse(await fs.readFile(root+'plans/'+name,'utf8')); const w=await SpreadsheetFile.importXlsx(await FileBlob.load(root+'authored/'+p.issue+'.xlsx'));
const original=new Map();
for(const c of cases[p.issue])for(const[sh,cs]of Object.entries(c.inputs))for(const a of Object.keys(cs)){const key=sh+'!'+a;if(!original.has(key))original.set(key,w.worksheets.getItem(sh).getRange(a).values[0][0]);}
for(const c of cases[p.issue]){
 for(const[key,v]of original){const n=key.lastIndexOf('!');w.worksheets.getItem(key.slice(0,n)).getRange(key.slice(n+1)).values=[[v??null]];}
 for(const[sh,cs]of Object.entries(c.inputs))for(const[a,v]of Object.entries(cs))w.worksheets.getItem(sh).getRange(a).values=[[v]];
 w.recalculate();let assertions=[];
 for(const[key,expected]of Object.entries(c.expect)){const n=key.lastIndexOf('!');const actual=w.worksheets.getItem(key.slice(0,n)).getRange(key.slice(n+1)).values[0][0];const pass=expected&&typeof expected==='object'?String(actual).includes(expected.contains):typeof expected==='number'?Math.abs(actual-expected)<.000001:actual===expected;assertions.push({key,expected,actual,pass});}
 const row={issue:p.issue,case:c.name,pass:assertions.every(x=>x.pass),assertions};results.push(row);console.log(p.issue,c.name,row.pass?'PASS':'FAIL',row.pass?'':JSON.stringify(assertions));
 await fs.writeFile(root+'regression-results.json',JSON.stringify(results,null,2));
}
}
if(results.some(x=>!x.pass))process.exitCode=1;
