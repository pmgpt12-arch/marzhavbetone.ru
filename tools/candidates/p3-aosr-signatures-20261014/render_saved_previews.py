"""Recreate optional page images from the retained exact QA PDFs, not new Office jobs."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
records=json.loads((ROOT/'selected-render-index.json').read_text())
for r in records:
    pdf=ROOT/r['pdf_path']
    assert hashlib.sha256(pdf.read_bytes()).hexdigest()==r['pdf_sha256'],'PDF drift'
    image_dir=ROOT/Path(r['page_images'][0]['path']).parent
    image_dir.mkdir(parents=True,exist_ok=True)
    cmd=['pdftoppm','-scale-to','1400','-png',str(pdf),str(image_dir/'page')]
    done=subprocess.run(cmd,capture_output=True,text=True,timeout=35)
    if done.returncode:raise RuntimeError(done.stderr)
    assert len(list(image_dir.glob('page-*.png')))==r['pages']
print('Current QA preview images regenerated; visual inspection and native Word remain separate checks.')
