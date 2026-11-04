#!/usr/bin/env python3
"""Bind the accepted P5 workbook to native Excel receipts and block 365-only regression."""
from pathlib import Path
import copy,hashlib,json,zipfile,xml.etree.ElementTree as E
from check_xlsx_print_contract import snapshot,compare
R=Path(__file__).resolve().parents[1]
D=R/'tools/nsp-product-audit-fixes-20261021/p5-final'
N={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def sha(b):return hashlib.sha256(b).hexdigest()
def validate_formulas(formulas,expected):
 return [address for address,value in expected.items()if formulas.get(address)!=value]
def main():
 accepted=json.loads((D/'acceptance.json').read_text())
 p=R/accepted['path'];assert sha(p.read_bytes())==accepted['accepted_sha256'],'Workbook changed: fresh native acceptance is required'
 with zipfile.ZipFile(p)as z:
  assert z.testzip()is None
  root=E.fromstring(z.read('xl/worksheets/sheet1.xml'))
  formulas={c.get('r'):c.findtext('s:f',namespaces=N)for c in root.findall('s:sheetData/s:row/s:c',N)if c.find('s:f',N)is not None}
  cells={c.get('r'):c for c in root.findall('s:sheetData/s:row/s:c',N)}
  strings=[''.join(t.itertext())for t in E.fromstring(z.read('xl/sharedStrings.xml'))]
  assert strings[int(cells['A25'].findtext('s:v',namespaces=N))]==accepted['label']
 assert not validate_formulas(formulas,accepted['formulas'])
 mutant=dict(formulas);mutant['G27']=accepted['original_formula_g27']
 assert validate_formulas(mutant,accepted['formulas'])==['G27'],'Missing negative formula control'
 baseline=json.loads((R/'tools/nsp-product-audit-fixes-20261021/p5-print-baseline.json').read_text())
 assert not compare(baseline['print_contract'],snapshot(p)),'Print contract changed'
 counts=[]
 for name in ('native-report.xml','reopen-report.xml'):
  raw=(D/name).read_bytes();assert sha(raw)==accepted['receipts'][name]
  report=E.fromstring(raw);checks=report.findall('check')
  assert report.get('status')=='PASS' and checks and all(x.get('pass','').lower()=='true'for x in checks),name
  assert not report.findall('error'),name
  counts.append(len(checks))
 assert counts==[72,9] and sum(counts)==81
 report=E.parse(D/'native-report.xml').getroot()
 source_check=next(c for c in report.findall('check')if c.get('name')=='p5fixed:input_sha')
 assert source_check.get('actual')==accepted['accepted_sha256']
 for entry in accepted['saved_files']:
  assert sha((D/entry['name']).read_bytes())==entry['sha256']
 assert accepted['print_review']=='PASS' and accepted['production_changed']is False
 print('PASS: P5 calendar-year formulas, native Excel 72+9 checks, source binding, print preservation; 365-only mutation detected')
if __name__=='__main__':main()
