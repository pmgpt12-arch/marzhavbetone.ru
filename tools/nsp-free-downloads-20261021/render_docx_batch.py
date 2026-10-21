#!/usr/bin/env python3
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
rows=json.loads((HERE/'docx-changes.json').read_text());start=int(sys.argv[1]);end=int(sys.argv[2]);out=Path('/tmp/nsp-free-docx-qa');out.mkdir(exist_ok=True)
for i in range(start,min(end,len(rows))):
 row=rows[i];p=ROOT/row['path'];dest=out/str(i);dest.mkdir(exist_ok=True)
 for old in list(dest.glob('page-*.png'))+list(dest.glob('*.pdf')):old.unlink()
 result=subprocess.run([sys.executable,'/root/.codex/skills/builtins/documents/render_docx.py',str(p),'--output_dir',str(dest),'--width','1100','--emit_pdf'],capture_output=True,timeout=45)
 (dest/'renderer.log').write_bytes(result.stdout+result.stderr)
 assert result.returncode==0 and list(dest.glob('page-*.png')),(i,result.stderr.decode()[-600:]);print('RENDERED',i,len(list(dest.glob('page-*.png'))),flush=True)
