from pathlib import Path
import json,hashlib,subprocess,shutil,re
from PIL import Image,ImageChops
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');S=Q/'office-resumed-products-20261023';R=Q.parent/'integration-20261022/repo'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((S/'RESULTS.json').read_text());assert len(rows)==3 and all(x['status']=='PASS'for x in rows)
for row in rows:
 if row['channel']=='word':
  assert len(row['files'])==3
  for x in row['files']:x['visual_review']='PASS_ALL_3_NATIVE_PAGES_VIEWED';x['content_review']='GUIDE_RECIPIENT_WORDING_OPEN; this does not establish full P11 release acceptance'
 elif 'avans-reopen'in row['job']:
  assert len(row['checks'])==9
  row['files'][0]['visual_review']='PASS_BOTH_NATIVE_PAGES_VIEWED';row['scope']='Saved-copy persistence check; does not replace source calculation tests'
 else:
  assert len(row['checks'])==30
  for x in row['files']:x['visual_review']='PRINT_REJECTED; partial visual inspection is sufficient to reject, not accept'
  row['print_findings']=[{'tag':'pp2','page':5,'finding':'Example label for alternative return is clipped at an adjacent occupied cell'},{'tag':'pp3','page':6,'finding':'Example print extends beyond the intended column L'},{'tag':'pp4','page':2,'finding':'21-column inventory shrinks across one A3 width; intended three print bands not applied'}]
(S/'RESULTS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
(S/'REVIEW.md').write_text('# Возобновлённая проверка Office, 23.10.2026\n\nWord: три точных исходника прошли нативное открытие и экспорт. Все девять страниц просмотрены. Пустая форма 54 и заполненные примеры 53/54 сохраняют письмо с подписью на странице 1, пояснения на страницах 2–3. В общем пояснении слово «Заказчику» следует заменить на «Адресату»: получателем по инструкции может быть цедент или застройщик. Эта редакционная поправка ещё не внесена; полный выпуск P11 не принят.\n\nExcel: сохранённый реестр «Аванс» повторно открыт, все девять проверок состояния пройдены. Просмотрены обе страницы повторного PDF. Это проверка сохранения результата, а не независимый повтор всех расчётных сценариев.\n\nP5: 30 расчётных и технических проверок прошли. Печатные варианты 22v2, 23v2 и 29v4 не приняты. На отдельных страницах уже достаточно доказательств отказа: обрезанный текст примера, лишняя правая колонка и неприменённые три полосы описи. Все 19 страниц печати P5 полностью не просмотрены, PASS им не присвоен. В квитанциях PageSetup.PrintArea и повторяемые заголовки пусты; встроенные имена после импорта представлены обычными именами.\n\nОтдельная минимальная диагностическая пара Latin/Cyrillic воспроизводит печать запрещённой колонки B при заданной области A1:A3 и IgnorePrintAreas=False. Исходные SHA сохранены. Это исключает кириллицу и сложную модель P5 как необходимые условия сбоя. Следующий тест меняет только представление пространства имён XML (префикс на default), сохраняя расширенные имена, атрибуты и текст элементов. QName-ошибка и ошибка сериализации различаются; причина на момент этого отчёта ещё не доказана.\n\nФайлы продукта, настройки Office, worker и службы не менялись этим этапом. Исходные ранее принятые материалы и публичная выдача сохранены.\n')
p=subprocess.run(['python3',str(Q/'scripts/verify_recovery_preservation_v2.py')],capture_output=True,text=True,timeout=30);assert p.returncode==0 and json.loads(p.stdout)['status']=='PASS';(S/'PRESERVATION_GATE.json').write_text(p.stdout)
for name in ['run_resumed_products.py','checkpoint_resumed_review.py']:shutil.copy2(Q/'scripts'/name,S/name)
shutil.copy2(Q/'resumed-products.log',S/'controller.log.txt')
rel='tools/nsp-next-corrections-20261022/office-resumed-products-20261023';D=R/rel;assert not D.exists();shutil.copytree(S,D,ignore=shutil.ignore_patterns('*.png'))
proof=[]
for png in S.rglob('*.png'):
 dst=(D/png.relative_to(S)).with_suffix('.webp');dst.parent.mkdir(parents=True,exist_ok=True);im=Image.open(png);im.save(dst,format='WEBP',lossless=True,method=6)
 assert ImageChops.difference(im.convert('RGBA'),Image.open(dst).convert('RGBA')).getbbox()is None
 proof.append({'source_png':str(png.relative_to(S)),'source_png_sha256':sha(png),'webp':str(dst.relative_to(D)),'webp_sha256':sha(dst),'pixels_identical':True})
(D/'PIXEL_PROOFS.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
for p in D.rglob('*'):
 if p.is_file():assert not re.search(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}',p.read_bytes()),p
inv=[{'path':str(p.relative_to(D)),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(D.rglob('*'))if p.is_file()]
(D/'FINAL_ARTIFACTS_SHA256.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
print('REVIEW_SNAPSHOT_READY',len(inv),'FILES',len(proof),'PAGES',flush=True)
