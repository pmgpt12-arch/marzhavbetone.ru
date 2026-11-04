from pathlib import Path
from xml.sax.saxutils import escape
import base64,zlib,json,hashlib,zipfile,copy,re,sys,xml.etree.ElementTree as E
Q=Path(__file__).resolve().parent;R=Q.parents[1]
SOURCE='products-storage/10-avans-usloviya-i-pribyl/02-kalkulyator-usloviy-avansa.xlsx'
sha=lambda b:hashlib.sha256(b).hexdigest()
raw_payload=zlib.decompress(base64.b64decode((Q/'patch-payload.z64').read_text()))
assert sha(raw_payload)=='335d2f84e72c7d6f8dca495fd565f6960bca247736b034e420b266c211f77fad','PAYLOAD_TRANSFER_MISMATCH'
(Q/'patch-payload.json').write_bytes(raw_payload);p=json.loads(raw_payload)
source=R/SOURCE;raw=source.read_bytes();assert sha(raw)==p['source_sha256'],'SOURCE_CHANGED'
changes=copy.deepcopy(p['cells'])
pattern=r'(?<![A-Za-z0-9_])(\$?[A-Z]{1,3})(\$?)([0-9]+)'
for t in p['templates']:
 for row in range(t['first'],t['last']+1):
  delta=row-t['first'];f=re.sub(pattern,lambda m:m[1]+m[2]+(m[3]if m[2]else str(int(m[3])+delta)),t['formula'])
  changes[t['sheet']][t['column']+str(row)]=f
assert sha(json.dumps(changes,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==p['all_expanded_cells_sha256'],'EXPANSION_MISMATCH'
N={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
z=zipfile.ZipFile(source);book=E.fromstring(z.read('xl/workbook.xml'));rels={x.get('Id'):x.get('Target')for x in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
paths={s.get('name'):rels[s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')].lstrip('/')for s in book.find('s:sheets',N)}
paths={k:v if v.startswith('xl/')else 'xl/'+v for k,v in paths.items()}
def colno(addr):
 n=0
 for c in re.match('[A-Z]+',addr)[0]:n=n*26+ord(c)-64
 return n
def cell_xml(sh,a,v,old):
 if old:
  start=re.match(r'<c\b([^>]*)',old)[1];start=re.sub(r'\s+t="[^"]*"','',start).rstrip('/')
 else:start=' r="'+a+'" s="'+str(p['cell_styles_for_additions'][sh][a])+'"'
 if isinstance(v,str)and v.startswith('='):return '<c'+start+'><f>'+escape(v[1:])+'</f><v/></c>'
 if isinstance(v,(int,float)):return '<c'+start+' t="n"><v>'+str(v)+'</v></c>'
 return '<c'+start+' t="inlineStr"><is><t>'+escape(str(v))+'</t></is></c>'
updates={};changed_count=0
for sh,items in changes.items():
 path=paths[sh];xml=z.read(path).decode();before=E.fromstring(xml);before_cells={c.get('r'):E.tostring(c)for c in before.findall('s:sheetData/s:row/s:c',N)}
 grouped={}
 for a,v in items.items():grouped.setdefault(int(re.search(r'\d+',a)[0]),{})[a]=v
 for rn,cells in sorted(grouped.items()):
  rx=re.compile(r'<row\b[^>]*\br="'+str(rn)+r'"[^>]*>.*?</row>',re.S);match=rx.search(xml)
  if match:row=match[0]
  else:row='<row r="'+str(rn)+'"></row>'
  for a,v in sorted(cells.items(),key=lambda x:colno(x[0])):
   cr=re.compile(r'<c\b[^>]*\br="'+a+r'"[^>]*(?:/>|>.*?</c>)',re.S);m=cr.search(row);new=cell_xml(sh,a,v,m[0]if m else None)
   if m:row=row[:m.start()]+new+row[m.end():]
   else:
    following=next((x for x in re.finditer(r'<c\b[^>]*\br="([A-Z]+[0-9]+)"',row)if colno(x[1])>colno(a)),None)
    pos=following.start()if following else row.index('</row>');row=row[:pos]+new+row[pos:]
   changed_count+=1
  height=p['row_heights'].get(sh,{}).get(str(rn))
  if height:
   start=re.match(r'<row[^>]*>',row)[0];new=re.sub(r'\s+(ht|customHeight)="[^"]*"','',start)[:-1]+' ht="'+str(height)+'" customHeight="1">';row=new+row[len(start):]
  if match:xml=xml[:match.start()]+row+xml[match.end():]
  else:
   later=next((x for x in re.finditer(r'<row\b[^>]*\br="(\d+)"',xml)if int(x[1])>rn),None);pos=later.start()if later else xml.index('</sheetData>');xml=xml[:pos]+row+xml[pos:]
 after=E.fromstring(xml);after_cells={c.get('r'):E.tostring(c)for c in after.findall('s:sheetData/s:row/s:c',N)}
 for a,b in before_cells.items():
  if a not in items:assert after_cells[a]==b,('UNEXPECTED_CELL_CHANGE',sh,a)
 for a,v in items.items():
  c=after.find('.//s:c[@r="'+a+'"]',N)
  if isinstance(v,str)and v.startswith('='):actual='='+c.findtext('s:f',namespaces=N)
  elif isinstance(v,(float,int)):actual=float(c.findtext('s:v',namespaces=N))
  else:actual=''.join(c.find('s:is',N).itertext())
  assert actual==v,('VALUE_MISMATCH',sh,a)
 updates[path]=xml.encode()
out=Q/'P8_02_for_manual_check_2026-10-22.xlsx'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)as dst:
 for info in z.infolist():dst.writestr(copy.copy(info),updates.get(info.filename,z.read(info.filename)))
with zipfile.ZipFile(out)as dst:
 assert dst.testzip()is None
 for name in z.namelist():
  E.fromstring(dst.read(name))
  if name not in updates:assert dst.read(name)==z.read(name)
 assert not any('vba' in x.lower()or 'externalLinks/'in x for x in dst.namelist())
sys.path.insert(0,str(R/'tools'));from check_xlsx_print_contract import snapshot,compare
errors=compare(snapshot(source),snapshot(out));assert not errors,errors
summary={'status':'CANDIDATE_FOR_OWNER_MANUAL_ACCEPTANCE','source_path':SOURCE,'source_sha256':sha(raw),'candidate_sha256':sha(out.read_bytes()),'candidate_bytes':out.stat().st_size,'changed_cells':changed_count,'changed_package_parts':sorted(updates),'original_print_contract':'PASS','non_target_cells_preserved':True,'other_package_parts_byte_identical':True,'row_height_adjustments':p['row_heights'],'calculation_model_tests':32,'calculation_model_assertions':132,'native_excel':'NOT_RUN; manual acceptance requested','visual_review_in_excel':'PENDING','production_changed':False,'customer_master_changed':False}
(Q/'STATUS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');(Q/'expanded-cells.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
assert sha(source.read_bytes())==p['source_sha256'];print(json.dumps(summary,ensure_ascii=False))
