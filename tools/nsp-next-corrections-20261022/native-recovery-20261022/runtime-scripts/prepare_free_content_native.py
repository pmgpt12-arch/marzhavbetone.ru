from pathlib import Path
q=Path(__file__).resolve().parent
s=(q/'native_free_word_v2.py').read_text()
changes={'nsp-free-word-layout-v2-20261022':'nsp-free-content-docx-20261022','FREE_DOCX_LAYOUT_V2.json':'FREE_CONTENT_DOCX_MANIFEST.json',"tag='fv'":"tag='fc'",'visual-free-v2':'visual-free-content','FREE_WORD_NATIVE_V2.json':'FREE_CONTENT_NATIVE.json'}
assert all(s.count(a)==1 for a in changes)
for a,b in changes.items():s=s.replace(a,b)
compile(s,'native_free_content.py','exec')
(q/'native_free_content.py').write_text(s)
print('CONTENT_NATIVE_CONTROLLER_PREPARED')
