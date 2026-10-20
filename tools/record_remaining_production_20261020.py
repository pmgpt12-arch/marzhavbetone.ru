#!/usr/bin/env python3
"""Persist actual HTTP-downloaded production ZIPs, hashes and acceptance state."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile,ZIP_DEFLATED
import json,os,shutil
R=Path(__file__).resolve().parents[1];B=R/'tools/candidates/remaining-batch-r3-20261018';O=B/'release-20261020'
source=Path(os.environ['RUNNER_TEMP'])/'remaining-live-buyer-evidence'
v=json.loads((source/'production-verification.json').read_text())
assert v['status']=='PASS_SCOPED_RELEASE_ACTUAL_HTTP_BUYER_ARCHIVES' and v['buyer_files']==123 and len(v['checks'])==9
out=O/'production';out.mkdir(exist_ok=True)
for p in v['checks']:
 f=source/p['production_zip'];assert sha256(f.read_bytes()).hexdigest()==p['production_sha256'];shutil.copyfile(f,out/f.name)
shutil.copyfile(source/'production-verification.json',out/'production-verification.json')
name='NSP_production_products_2026-10-20.zip';bundle=out/name
with ZipFile(bundle,'w',ZIP_DEFLATED) as z:
 for p in v['checks']:z.write(out/p['production_zip'],p['production_zip'])
 z.writestr('00-SOSTAV.txt','На стороне подрядчика. Опубликованные комплекты — 20.10.2026.\n\nВосемь основных систем: P1, P2, P4, P7, P8, P9, P10, P13.\nОтдельно — адресная редакция АОСР в P3.\nВсего 123 покупательских файла. Их содержимое совпадает с согласованной редакцией.\nАрхивы получены через действующий механизм скачивания сайта.\n')
with ZipFile(bundle) as z:assert len(z.namelist())==10 and z.testzip() is None
v['bundle']={'file':name,'sha256':sha256(bundle.read_bytes()).hexdigest(),'bytes':bundle.stat().st_size,'outer_entries':10}
(out/'production-verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
plan=json.loads((O/'release-plan.json').read_text());plan['production']='PASS_ACTUAL_HTTP_ARCHIVES';plan['production_evidence']='production/production-verification.json';(O/'release-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
p=B/'evidence/working-checkpoint.json';d=json.loads(p.read_text());d.update(status='OWNER_ACCEPTED_PRODUCTION_RELEASE_VERIFIED',production_evidence='../release-20261020/production/production-verification.json');p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
p=B/'REVIEW-STATUS.md';p.write_text(p.read_text()+'\n## Размещение подтверждено — 20.10.2026\n\nВладелец согласовал файлы и разрешил публикацию: «Файлы согласованы, сохраняй и размещай». Адресный выпуск восьми комплектов и исправления АОСР P3 подтверждён скачиванием девяти фактических архивов: 123/123 SHA файлов, CRC, 13 позиций каталога, цены, письма (без отправки), HTTP 200 действующих ссылок и HTTP 410 истёкших. Синтетические заказы удалены. Общий деплой не выполнялся. Защищённые мастера и кэши прочих продуктов сохранены по SHA. Точные production ZIP и результаты — release-20261020/production/.\n')
print(json.dumps(v['bundle'],ensure_ascii=False))
