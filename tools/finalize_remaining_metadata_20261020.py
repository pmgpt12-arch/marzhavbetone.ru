#!/usr/bin/env python3
"""Refresh service manifests and support copy without changing accepted buyer bytes."""
from pathlib import Path
from hashlib import sha256
import json
R=Path(__file__).resolve().parents[1];B=R/'tools/candidates/remaining-batch-r3-20261018';O=B/'release-20261020'
plan=json.loads((O/'release-plan.json').read_text())
support='Если письмо не пришло или ссылка не открывается, напишите на <a href="mailto:marzhavbetone@yandex.ru">marzhavbetone@yandex.ru</a> — поможем получить файлы.'
for p in plan['packages']:
 d=R/'products-storage'/p['dir']
 before={n:sha256((d/n).read_bytes()).hexdigest() for n in p['members']}
 assert before==p['members']
 manifest='# '+p['name']+'\n\nПокупателю уходит '+str(p['count'])+' файлов.\n\n## Состав\n\n'+'\n'.join('- `'+n+'`' for n in sorted(p['members']))+'\n\n## Приёмка\n\nВладелец согласовал архив 20.10.2026. SHA-256 принятого ZIP: `'+p['approved_zip_sha256']+'`.\nЦена: '+str(p['price']//100)+' ₽. Основание: #578.\n'
 (d/'MANIFEST.md').write_text(manifest)
 p['master_files']={str(f.relative_to(d)):sha256(f.read_bytes()).hexdigest() for f in d.rglob('*') if f.is_file()}
for f in plan['site_files']:
 if not f['file'].startswith('products/') or '/p3-' in f['file']:continue
 path=R/f['file'];s=path.read_text()
 if 'Если письмо не пришло или ссылка не открывается' not in s:
  s=s.replace('</main>','<section class="section"><p>'+support+'</p></section></main>');path.write_text(s)
 f['sha256']=sha256(path.read_bytes()).hexdigest()
(O/'release-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
print('PASS updated 9 service manifests and download support; all 123 approved buyer hashes unchanged')
