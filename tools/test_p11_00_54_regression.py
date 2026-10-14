"""P11: fail-closed outgoing-letter and START HERE regression checks.
Run: python tools/test_p11_00_54_regression.py --root .
Reads the two candidate files only; mutations are in memory. No Office/network.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
CANDIDATE = Path('tools/candidates/portfolio-owner-pdf-20261013/13-raschet-metrami')
REQUIRED = ('СРОК_ОТВЕТА_НА_ЗАПРОС', 'АДРЕС_ДЛЯ_ОТВЕТА', 'ЭЛЕКТРОННАЯ_ПОЧТА')
FILES = ('00-START-HERE.txt', '50-slovar-poley-raschet-metrami.docx',
         '51-algoritm-raschet-metrami.pdf', '52-chek-list-raschet-metrami.docx',
         '53-zapros-status-obekta.docx', '54-zapros-sostoyanie-escrow.docx',
         '55-pamyatka-punkt-ustupki-escrow.pdf', '56-pervyy-den-do-podpisi.docx')

def check(xml: str, start: str) -> dict:
    root = ET.fromstring(xml)
    pars = root.find(W+'body').findall(W+'p')
    texts = [''.join(t.text or '' for t in p.iter(W+'t')) for p in pars]
    begins = [i for i,t in enumerate(texts) if t.startswith('Кому:')]
    ends = [i for i,t in enumerate(texts) if t == 'Как пользоваться этим документом']
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        return {'verdict':'FAIL','checks':{'outgoing_boundary':False}}
    outgoing = '\n'.join(texts[begins[0]:ends[0]])
    checks = {'outgoing_'+key: '{{'+key+'}}' in outgoing for key in REQUIRED}
    checks['numbering_1_2_3'] = re.findall(r'^(\d+)\. ',outgoing,re.M) == ['1','2','3']
    checks['legal_point_preserved'] = ('ч. 3 ст. 11 Закона № 214-ФЗ' in outgoing and 'При зачёте работ — основание и момент зачёта.' in outgoing)
    headings = []
    for p,t in zip(pars,texts):
        prop = p.find(W+'pPr/'+W+'pStyle')
        headings.append((t,prop.get(W+'val') if prop is not None else None))
    checks['when_applies_heading'] = sum(t=='Когда применяется' and s=='Heading2' for t,s in headings) == 1
    legal = [(t,s) for t,s in headings if t.startswith('Сверьте оплату ДДУ по банковскому подтверждению')]
    checks['legal_guide_normal_paragraph'] = len(legal)==1 and legal[0][1] not in ('Heading1','Heading2')
    compact = ' '.join(start.split())
    checks['start_steps'] = ('Запрос об эскроу (54) направляют на шаге 2, запрос о статусе объекта (53) — на шаге 3.' in compact)
    checks['start_formats'] = ('В Word редактируются словарь полей (50), чек-лист (52), запросы (53, 54) и маршрут первого дня (56).' in compact and 'В PDF представлены алгоритм (51) и памятка (55).' in compact and 'Excel' not in start)
    section = re.search(r'4\. ЧТО В АРХИВЕ\n(.*?)\n5\. ЗАДАЧА',start,re.S)
    listed = re.findall(r'^\s+([0-9]{2}-[^\s]+\.(?:txt|docx|pdf))',section.group(1),re.M) if section else []
    checks['manifest_eight_exact_names'] = tuple(listed)==FILES
    checks['numbering_not_route'] = 'Порядок применения указан в разделе 3 и в алгоритме, а не в номерах файлов.' in compact
    sample = dict(zip(REQUIRED,('20.10.2026','Тестовый адрес для ответа','qa@example.invalid')))
    filled = outgoing
    for key,value in sample.items(): filled = filled.replace('{{'+key+'}}',value)
    checks['filled_reply_values'] = all(value in filled for value in sample.values())
    return {'verdict':'PASS' if all(checks.values()) else 'FAIL','checks':checks}

def negative_tests(xml: str, start: str) -> dict:
    mutants = {f'missing_{key}':(xml.replace('{{'+key+'}}',''),start) for key in REQUIRED}
    mutants.update({
        'duplicate_point3': (xml.replace('2. Сведения','3. Сведения',1),start),
        'missing_heading': (xml.replace('Когда применяется','Удалённый заголовок',1),start),
        'missing_legal_point': (xml.replace('При зачёте работ — основание и момент зачёта.',''),start),
        'wrong_step': (xml,start.replace('направляют на шаге 2','направляют на шаге 3',1)),
        'false_excel': (xml,start+'\nExcel\n'),
        'wrong_format': (xml,start.replace('алгоритм (51) и памятка (55)','чек-лист (52) и памятка (55)',1)),
        'missing_file': (xml,start.replace('   50-slovar-poley-raschet-metrami.docx\n','',1)),
        'missing_boundary': (xml.replace('>Как пользоваться этим документом<','>Другая инструкция<',1),start),
    })
    root = ET.fromstring(xml)
    for p in root.find(W+'body').findall(W+'p'):
        if ''.join(t.text or '' for t in p.iter(W+'t')).startswith('Сверьте оплату ДДУ по банковскому подтверждению'):
            prop=p.find(W+'pPr')
            if prop is None: prop=ET.SubElement(p,W+'pPr')
            style=prop.find(W+'pStyle')
            if style is None: style=ET.SubElement(prop,W+'pStyle')
            style.set(W+'val','Heading2')
    mutants['legal_misstyled_heading']=(ET.tostring(root,encoding='unicode'),start)
    return {name:check(x,s)['verdict']=='FAIL' for name,(x,s) in mutants.items()}

def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--candidate-dir',type=Path)
    ap.add_argument('--report',type=Path)
    args=ap.parse_args()
    base=args.candidate_dir or args.root/CANDIDATE
    doc=base/FILES[5]; start_file=base/FILES[0]
    with ZipFile(doc) as z:
        if z.testzip() is not None: raise ValueError('ZIP_CRC_FAILURE')
        xml=z.read('word/document.xml').decode('utf-8')
    start=start_file.read_text(encoding='utf-8')
    result=check(xml,start); result['negative_tests']=negative_tests(xml,start)
    result['input_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (doc,start_file)}
    result['scope']='TWO_FILES_STATIC_ONLY_NOT_NATIVE_OR_PRODUCT_ACCEPTANCE'
    result['verdict']='PASS' if result['verdict']=='PASS' and all(result['negative_tests'].values()) else 'FAIL'
    data=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.report: args.report.write_text(data,encoding='utf-8')
    print(data,end='')
    raise SystemExit(0 if result['verdict']=='PASS' else 1)

if __name__=='__main__': main()
