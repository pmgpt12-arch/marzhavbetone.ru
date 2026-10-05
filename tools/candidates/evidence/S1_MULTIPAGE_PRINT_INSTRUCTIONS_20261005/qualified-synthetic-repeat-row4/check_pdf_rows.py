from pathlib import Path
import xml.etree.ElementTree as E,json,collections,re,datetime,decimal
r=Path(__file__).resolve().parent;receipt=json.loads((r/'receipt.json').read_text());e=receipt['runs'][0];ns={'x':'http://www.w3.org/1999/xhtml'};pages=E.parse(r/'long-64-operations.bbox.xhtml').getroot().findall('.//x:page',ns)
results=[];identifiers=[];running=0;page_results=[]
for pno,p in enumerate(pages,1):
 words=p.findall('.//x:word',ns);ops=[w for w in words if re.fullmatch(r'LONG-OP-\d{3}',w.text or '')];ops.sort(key=lambda w:float(w.attrib['yMin']))
 page_results.append({'page':pno,'operation_ids':[w.text for w in ops],'header_date_present':any(w.text=='Дата' for w in words)})
 widths=e['widths_after'][:10];left=e['settings_after']['page_properties']['LeftMargin']*72/2540;scale=(float(p.attrib['width'])-left-e['settings_after']['page_properties']['RightMargin']*72/2540)/sum(widths);bound=[left]
 for width in widths:bound.append(bound[-1]+width*scale)
 def colws(col,y):
  i=ord(col)-65
  return sorted([w for w in words if abs(float(w.attrib['yMin'])-y)<.2 and bound[i]<=((float(w.attrib['xMin'])+float(w.attrib['xMax']))/2)<bound[i+1]],key=lambda w:float(w.attrib['xMin']))
 for j,w in enumerate(ops):
  token=w.text;identifiers.append(token);idx=int(token[-3:])-1;y=float(w.attrib['yMin']);num=idx+1;aid='TEST-A' if idx%4<2 else 'TEST-B';amount=(10000 if aid=='TEST-A' else 20000) if idx%2==0 else (1000 if aid=='TEST-A' else 2000);impact=amount if idx%2==0 else -amount;running+=impact
  def txt(c):return ''.join(x.text or '' for x in colws(c,y))
  def number(c):return float(decimal.Decimal(txt(c).replace(',','.')))
  expected_date=(datetime.date(1899,12,30)+datetime.timedelta(days=46266+idx)).strftime('%d.%m.%Y')
  actual={'row_number':int(txt('A')),'date':txt('B'),'document':txt('D'),'amount':number('E'),'act_id':txt('F'),'impact':number('G'),'disputed':number('H'),'check':txt('I'),'running_balance':number('J')}
  expected={'row_number':num,'date':expected_date,'document':token,'amount':amount,'act_id':aid,'impact':impact,'disputed':0,'check':'ок','running_balance':running}
  results.append({'page':pno,'operation':token,'actual':actual,'expected':expected,'pass':actual==expected})
coverage=collections.Counter(identifiers);expected_ids=[f'LONG-OP-{i:03d}' for i in range(1,65)]
summary={'status':'ROW_CONTENT_PASS_HEADER_CHECK_PENDING','rows_checked':len(results),'all_rows_pass':all(v['pass'] for v in results),'exact_id_sequence':identifiers==expected_ids,'duplicates':{k:v for k,v in coverage.items() if v!=1},'missing':[x for x in expected_ids if x not in coverage],'final_running_balance':running,'page_breaks':page_results,'repeated_header_gate':all(p['header_date_present'] for p in page_results),'visual_gate':'PENDING_ROOT_ALL_FOUR_PAGES','native_preserved':receipt['native_preserved'],'excel_manual_pass':False}
assert len(results)==64 and summary['all_rows_pass'] and summary['exact_id_sequence'],summary
(r/'row-content-evidence.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));(r/'multipage-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='page_breaks'},ensure_ascii=False,indent=2))
