"""Strict per-act structure and exact-delta checks; never issues independent PASS."""
import hashlib, io, json, re, subprocess
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
ROOT=Path(__file__).resolve().parent
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def sha(b): return hashlib.sha256(b).hexdigest()
def paragraphs(data):
    with ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None
        root=etree.fromstring(z.read('word/document.xml'))
    return [''.join((x.text or '') if x.tag==W+'t' else '\n' for x in p.iter() if x.tag in [W+'t',W+'br']) for p in root.iter(W+'p')]
def validate_acts(ps):
    starts=[i for i,p in enumerate(ps) if p.startswith('АКТ ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ — ')]
    assert len(starts)==5,'five full act blocks'
    for n,start in enumerate(starts,1):
        block=ps[start:starts[n] if n<len(starts) else len(ps)]
        assert len(block)==53,'master paragraph structure'
        for sec in range(1,8):assert sum(p.startswith(str(sec)+'. ') for p in block)==1,'missing/duplicate section'
        assert sum(p=='Подписи представителей' for p in block)==1
        assert sum('Подпись __________________' in p for p in block)==5
        text='\n'.join(block)
        tokens=re.findall(r'\{\{([^{}]+)\}\}',text)
        assert len(tokens)==27 and len(set(tokens))==27,'incomplete field set'
        assert all(t.startswith('A'+str(n)+'_') for t in tokens),'mixed-act fields'
        assert text.count('если привлечен для проверки соответствия работ проекту')==2
        assert text.count('если работы выполнены иным лицом по договору')==2
        assert not any(s in text.lower() for s in ['подписи всех трех','[форма с','[форма акта','универсальный форма'])
    return True
report=json.loads((ROOT/'author-structural.json').read_text())
positive={};negative={}
for entry in report['artifacts']:
    name=entry['file'];data=(ROOT/'candidate'/name).read_bytes()
    assert sha(data)==entry['sha256'],'output drift '+name
    paragraphs(data);positive['identity_crc_'+name]=True
for name,mapping in report['source_deltas'].items():
    original=(ROOT/'inputs'/name).read_bytes();new=(ROOT/'candidate'/name).read_bytes()
    expected=[mapping.get(p,p) for p in paragraphs(original)]
    assert paragraphs(new)==expected,'unlisted textual delta'
    with ZipFile(io.BytesIO(original)) as a,ZipFile(io.BytesIO(new)) as b:
        assert a.namelist()==b.namelist()
        assert [n for n in a.namelist() if a.read(n)!=b.read(n)]==['word/document.xml']
    positive['exact_full_document_delta_'+name]=True
ps=paragraphs((ROOT/'candidate/03-akt-skrytyh-rabot.docx').read_bytes())
validate_acts(ps);positive['five_act_individual_fields_sections_signatures']=True
start=next(i for i,p in enumerate(ps) if p.startswith('АКТ ОСВИДЕТЕЛЬСТВОВАНИЯ'))
mutations={
 'missing_act':ps[:start]+ps[start+53:],
 'missing_section7':[p for i,p in enumerate(ps) if i!=start+35],
 'lost_date_field':[p.replace('{{A1_ДАТА_АКТА}}','') for p in ps],
 'mixed_act_token':[p.replace('{{A1_ОБЪЕКТ}}','{{A2_ОБЪЕКТ}}') for p in ps],
 'lost_signature':[p for i,p in enumerate(ps) if i!=start+44],
 'unconditional_designer':[p.replace('(если привлечен для проверки соответствия работ проекту)','(обязательно во всех случаях)') for p in ps],
 'description_instead_of_act':ps[:start]+['[Форма акта с полями]']+ps[start+53:],
 'old_v3_stub':paragraphs((ROOT/'inputs/03-akt-skrytyh-rabot.docx').read_bytes())}
for name,bad in mutations.items():
    try:validate_acts(bad)
    except AssertionError:negative[name]='DETECTED'
    else:raise AssertionError('Mutation escaped: '+name)
result={'status':'PASS_AUTHOR_STRUCTURE_AND_DELTA_ONLY','positive_checks':positive,'negative_checks':negative,'positive_passed':len(positive),'negative_detected':len(negative),'independent_acceptance':'PENDING','native_word':'NOT_RUN','release':'HOLD'}
(ROOT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
if '--render' in __import__('sys').argv:
    index=[]
    for pdf in sorted((ROOT/'render').glob('*.pdf')):
        dest=ROOT/'render'/pdf.stem;dest.mkdir(exist_ok=True)
        command=['pdftoppm','-scale-to','1400','-png',str(pdf),str(dest/'page')]
        done=subprocess.run(command,capture_output=True,text=True,timeout=35)
        if done.returncode:raise RuntimeError(done.stderr)
        images=sorted(dest.glob('page-*.png'))
        index.append({'source_docx':pdf.stem+'.docx','source_sha256':sha((ROOT/'candidate'/(pdf.stem+'.docx')).read_bytes()),'pdf_sha256':sha(pdf.read_bytes()),'pages':len(images),'images':[{'path':str(p),'sha256':sha(p.read_bytes())} for p in images]})
    (ROOT/'render-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    print('RENDER_INDEX',json.dumps([{'name':r['source_docx'],'pages':r['pages']} for r in index]))
