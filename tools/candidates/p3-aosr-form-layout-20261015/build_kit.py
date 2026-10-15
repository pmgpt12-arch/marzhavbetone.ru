#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,zipfile,io,re
from docx import Document
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BEFORE=ROOT/'p3-buyer-final-v2-20261015/P3-11-buyer-revised-20261015.zip'
AFTER=HERE/'P3-11-buyer-AOSR-formatted-20261015.zip'
NEW=HERE/'03-akt-skrytyh-rabot.docx'
PDF=HERE/'qa-render-v3/03-akt-skrytyh-rabot.pdf'
EXPECTED_BEFORE='44effd5122826ca6950e69806e0bf36ec0dd0cd7b142d58f29b3075ac94ac451'
EXPECTED_DOC='cd8e5d4b1533bbbfebb3d85a06784a1b861ef6a8b54bcfb027d557fcb64bfdb5'
NAME='03-akt-skrytyh-rabot.docx'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(BEFORE.read_bytes())==EXPECTED_BEFORE
assert PDF.is_file() and PDF.stat().st_size>2000
src=zipfile.ZipFile(BEFORE)
names=src.namelist()
assert len(names)==11 and NAME in names
assert sha(src.read(NAME))==EXPECTED_DOC
source_contents={n:src.read(n) for n in names}
with zipfile.ZipFile(AFTER,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as dest:
 for original in src.infolist():
  data=NEW.read_bytes() if original.filename==NAME else source_contents[original.filename]
  dest.writestr(original,data)
with zipfile.ZipFile(AFTER) as result:
 assert result.namelist()==names and result.testzip() is None
 src_stats={n:sha(source_contents[n]) for n in names}
 out_stats={n:sha(result.read(n)) for n in names}
 unchanged=[n for n in names if n!=NAME and src_stats[n]==out_stats[n]]
 assert len(unchanged)==10
 assert src_stats[NAME]!=out_stats[NAME]
 srcdoc=Document(io.BytesIO(source_contents[NAME]))
 newdoc=Document(io.BytesIO(result.read(NAME)))
 original_text=[p.text for p in srcdoc.paragraphs]
 from docx.oxml.ns import qn
 newtext=' '.join(t.text or '' for t in newdoc.element.body.iter(qn('w:t')))
 tok=lambda s:sorted(re.findall(r'\{\{[^{}]+\}\}',s))
 assert tok('\n'.join(original_text))==tok(newtext)
 manifest={'base_pr':651,'base_head':'b8758c6759f10dba9f3e8c409640663cefb6bdfa',
 'base_zip_sha256':EXPECTED_BEFORE,
 'formatted_docx_sha256':sha(NEW.read_bytes()),
 'archive_sha256':sha(AFTER.read_bytes()),'count':11,
 'exact_unchanged_members':len(unchanged),
 'changed_member':NAME,'member_sha256':out_stats,'original_member_sha256':src_stats,
 'all_135_placeholders_retained':len(tok(newtext))==135,
 'original_5_forms_retained':len([p for p in original_text if p.startswith('АКТ ОСВИДЕТЕЛЬСТВОВАНИЯ СКРЫТЫХ РАБОТ')])==5,
 'open_gates':['native Microsoft Word exact-SHA visual/open/export','independent owner look of current form','full G1-G8','formal nomination'],
 'release':'HOLD'}
(HERE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:manifest[k] for k in ('archive_sha256','formatted_docx_sha256','exact_unchanged_members','all_135_placeholders_retained','count')},ensure_ascii=False))
