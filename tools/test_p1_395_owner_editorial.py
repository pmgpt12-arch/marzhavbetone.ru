#!/usr/bin/env python3
"""Owner text/style/print regression. No native replay and no release approval."""
from pathlib import Path
import importlib.util, copy, hashlib, io, json, zipfile
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'tools/candidates/p1-395-owner-editorial-20261013'
spec=importlib.util.spec_from_file_location('owner_editorial_delta',FOLDER/'build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
SRC=ROOT/'tools/candidates/p1-395-content-20261012/14-raschet-procentov-395-gk.xlsx'
FILE=FOLDER/'14-raschet-procentov-395-gk.xlsx'
EXPECTED='d29a0fd17baa090d6d98443c984cf33109316ffda8a346e8ea5a7e74ae85b52d'
def mutate(raw,part,old,new):
 out=io.BytesIO()
 with zipfile.ZipFile(io.BytesIO(raw)) as z,zipfile.ZipFile(out,'w') as target:
  for info in z.infolist():
   data=z.read(info.filename)
   if info.filename==part:
    assert old in data,('MUTATION_ANCHOR_MISSING',part)
    data=data.replace(old,new,1)
   target.writestr(info,data)
 return out.getvalue()
def check_receipt(record,raw):
 assert record['candidate_sha256']==hashlib.sha256(raw).hexdigest()==EXPECTED
 assert record['source_sha256']==build.SHA
 assert record['status']=='PASS_OWNER_TEXT_STYLE_PRINT_CONFIGURATION_ONLY'
 assert record['native_office']=='PENDING_NEW_SHA' and record['visual']=='PENDING_NEW_SHA'
 assert record['g1_g8']=='HOLD' and record['release']=='BLOCKED'
 assert record['checks']['formulas_preserved']==251
 assert record['checks']['print_area']=="'Расчёт'!$A$1:$H$46"
 assert record['source_modified'] is False and record['production_modified'] is False

def main():
 source=SRC.read_bytes();raw=FILE.read_bytes()
 assert hashlib.sha256(source).hexdigest()==build.SHA
 assert hashlib.sha256(raw).hexdigest()==EXPECTED
 result=build.verify(source,raw)
 receipt=json.loads((FOLDER/'receipt.json').read_text());check_receipt(receipt,raw)
 policy=json.loads((ROOT/'tools/buyer_editorial_policy.json').read_text())
 assert policy['decision_id']=='MB001-EDITORIAL-OWNER-20261013'
 assert len(set(policy['target_skus']))==13
 assert policy['italic_allowed'] is False and policy['semantic_review_required'] is True
 fixtures=[
  ('formula', 'xl/worksheets/sheet2.xml', b'<f>',b'<f>1+'),
  ('italic', 'xl/styles.xml', b'<font>',b'<font><i/>'),
  ('print_range', 'xl/workbook.xml',b'$H$46',b'$H$45'),
  ('forbidden_column','xl/worksheets/sheet2.xml','Столбец'.encode(),'Колонка'.encode()),
  ('forbidden_color','xl/worksheets/sheet1.xml','бежевой'.encode(),'светло-золотистой'.encode()),
  ('filler','xl/worksheets/sheet2.xml','Столбец'.encode(),'Остальное считается само. Столбец'.encode()),
  ('bold_loss','xl/styles.xml',b'<b val="1"/>',b'<b val="0"/>')]
 rejected=[]
 for label,part,old,new in fixtures:
  bad=mutate(raw,part,old,new)
  try:build.verify(source,bad)
  except AssertionError:rejected.append(label)
  else:raise AssertionError('REGRESSION_NOT_DETECTED:'+label)
 bad=copy.deepcopy(receipt);bad['native_office']='PASS'
 try:check_receipt(bad,raw)
 except AssertionError:rejected.append('false_native_acceptance')
 else:raise AssertionError('FALSE_NATIVE_ACCEPTANCE_NOT_DETECTED')
 assert len(rejected)==8
 print(json.dumps({'status':'PASS_OWNER_EDITORIAL_DELTA_ONLY','sha256':EXPECTED,'formulas':251,'text_cells':5,'active_italic':0,'print_area':result['print_area'],'negative_cases':rejected,'g1_g8':'OPEN'},ensure_ascii=False))
 return 0
if __name__=='__main__':raise SystemExit(main())
