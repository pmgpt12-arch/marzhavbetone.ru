from pathlib import Path
import json,hashlib,shutil,subprocess,re
from PIL import Image,ImageChops
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');R=Q.parent/'integration-20261022/repo';S=Q/'p11-guide-r4-20261023';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((S/'RESULTS.json').read_text());assert r['status']=='PASS'and len(r['files'])==4
for x in r['files']:assert x['native_pages']==3;x['visual_review']='PASS_ALL_3_NATIVE_PAGES_VIEWED'
(S/'RESULTS.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
source=''.join(json.loads(l)for l in (Q/'p11-guide-source-chunks.jsonl').read_text().splitlines());assert len(json.loads(source))==4;(S/'source-transfer.json').write_text(source+'\n')
for name in ['run_p11_guide_r4.py','finalize_p11_guide_receipt.py','build_p11_r4_package.py','checkpoint_p11_r4.py']:shutil.copy2(Q/'scripts'/name,S/name)
for name in ['p11-guide-r4.log','p11-guide-finalize.log','build-p11-r4.log']:shutil.copy2(Q/name,S/(name+'.txt'))
(S/'README.md').write_text('# P11 новые формы 53 и 54\n\nИсправлена роль получателя в пояснении: «Адресату» вместо «Заказчику». Изменён ровно один фрагмент в каждой форме и в двух учебных заполнениях. Отправляемый текст и все прочие части DOCX сохранены. Ранее принятые 52 и 56 не пересохранялись.\n\nВсе четыре точных SHA прошли Word 2016. Все 12 нативных страниц просмотрены. В формах и заполненных примерах отправляемое письмо и подпись помещаются на странице 1, пояснения идут после разрыва. Все 12 страниц отдельного канонического render_docx.py также просмотрены. Структурная проверка подтверждает единственное текстовое изменение и побайтное равенство всех прочих частей DOCX.\n\nПересобран полный QA ZIP P11 из восьми файлов штатным неизменённым сборщиком. SHA fca8d1c4d525dce05b0760367d0c9ae4dcd60085ace8f9d2b22d97c580415ac9. Проверены CRC, состав, SHA каждого вложения, ровно два изменения относительно предыдущего полного QA ZIP. Учебные заполнения в архив не входят. Шесть остальных файлов сохранены побайтно; прежние нормативные и нативные проверки относятся к прежним точным SHA и повторно не выдаются за новые.\n\nИсторическая ошибка постобработчика сохранена: он ожидал маркер подписи другого шаблона. После исправления проверяющего условия разобрана та же существующая PASS-квитанция, без повторной отправки задания и без изменения документов.\n\nЭто результат этапа QA. Публичная выдача, канонические мастера и main не переключались. Вся продуктовая линейка завершённой не объявляется; P5 по-прежнему не принят по печати.\n')
p=subprocess.run(['python3',str(Q/'scripts/verify_recovery_preservation_v2.py')],capture_output=True,text=True,timeout=30);assert p.returncode==0 and json.loads(p.stdout)['status']=='PASS';(S/'PRESERVATION_GATE.json').write_text(p.stdout)
rel='tools/nsp-next-corrections-20261022/p11-guide-r4-20261023';D=R/rel;assert not D.exists();shutil.copytree(S,D,ignore=shutil.ignore_patterns('*.png'))
proof=[]
for png in S.rglob('*.png'):
 dst=(D/png.relative_to(S)).with_suffix('.webp');dst.parent.mkdir(parents=True,exist_ok=True);im=Image.open(png);im.save(dst,format='WEBP',lossless=True,method=6);assert ImageChops.difference(im.convert('RGBA'),Image.open(dst).convert('RGBA')).getbbox()is None
 proof.append({'png':str(png.relative_to(S)),'png_sha256':sha(png),'webp':str(dst.relative_to(D)),'sha256':sha(dst),'pixels_identical':True})
assert len(proof)==12;(D/'PIXEL_PROOFS.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
for p in D.rglob('*'):
 if p.is_file():assert not re.search(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}',p.read_bytes()),p
inv=[{'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(D.rglob('*'))if p.is_file()];(D/'FINAL_ARTIFACTS_SHA256.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
print('P11_SNAPSHOT_READY',len(inv),'FILES',flush=True)
