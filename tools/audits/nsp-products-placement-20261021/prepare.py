from pathlib import Path
from hashlib import sha256
import json,subprocess
cfg=json.loads('{"p1":["01-zakrytie-rabot",20,2990000],"p2":["02-dopraboty-bez-poter",15,2490000],"p3":["05-ks-bez-vozvrata",11,1790000],"p4":["08-pto-bez-zamechaniy",25,2490000],"p5":["07-uderzhaniya-shtrafy-zachety",30,2990000],"p7":["03-dogovor-podryada",13,2490000],"p8":["10-avans-usloviya-i-pribyl",11,2490000],"p9":["11-bankrotstvo-genpodryadchika",10,2490000],"p10":["15-otvet-na-pretenziyu-baza",8,1790000],"p11":["13-raschet-metrami",8,2490000],"p13":["16-chto-v-smete-ne-oplatyat",10,1790000],"t2":["14-peredacha-id-pod-podpis",6,990000],"t3":["17-odnostoronniy-akt-i-zachet",5,1490000]}')
base=Path('products-storage');expected={}
plan=json.loads(Path('tools/candidates/remaining-batch-r3-20261018/release-20261020/release-plan.json').read_text())
approved={x['sku']:x['members'] for x in plan['packages']}
for sku,(directory,count,price) in cfg.items():
 root=base/directory
 members={str(f.relative_to(root)):sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file() and f.name not in {'.htaccess','MANIFEST.md','00-PISMO-POSLE-POKUPKI.txt'}}
 assert len(members)==count,(sku,len(members))
 if sku in approved:assert members==approved[sku],sku
 expected[sku]={'dir':directory,'price':price,'members':dict(sorted(members.items()))}
assert sum(len(x['members']) for x in expected.values())==172
php=Path('tools/audits/nsp-products-placement-20261021/audit.php').read_text().replace('EXPECTED_JSON', 'json_decode('+json.dumps(json.dumps(expected,ensure_ascii=False))+',true)')
Path('/tmp/nsp-placement-audit.php').write_text(php)
