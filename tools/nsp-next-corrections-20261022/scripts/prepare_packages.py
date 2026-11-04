from pathlib import Path
from zipfile import ZipFile
import json,hashlib,shutil,subprocess
Q=Path(__file__).resolve().parents[1];R=Q.parent/'integration-20261022/repo';manifest=json.loads((Q/'new-workbook-manifest.json').read_text())+json.loads((Q/'content-manifest.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='203b39a390c09157adcd6760aa04318df332bedc'
protected=json.loads((Q.parent/'integration-20261022/MANIFEST_VERIFIED_FILES.json').read_text())['files']
for f in protected:assert sha((R/f['path']).read_bytes())==f['accepted_sha256']
products={'P1':'01-zakrytie-rabot','P2':'02-dopraboty-bez-poter','P3':'05-ks-bez-vozvrata','P4':'08-pto-bez-zamechaniy','P5':'07-uderzhaniya-shtrafy-zachety','P7':'03-dogovor-podryada','P8':'10-avans-usloviya-i-pribyl','P9':'11-bankrotstvo-genpodryadchika','P10':'15-otvet-na-pretenziyu-baza','P11':'13-raschet-metrami','P13':'16-chto-v-smete-ne-oplatyat','T2':'14-peredacha-id-pod-podpis','T3':'17-odnostoronniy-akt-i-zachet'}
service={'.htaccess','00-PISMO-POSLE-POKUPKI.txt','MANIFEST.md'};inventory=[]
for sku,folder in products.items():
 source=R/'products-storage'/folder;dest=Q/'package-sources/products-storage'/folder;shutil.copytree(source,dest,dirs_exist_ok=True)
 for f in sorted(source.rglob('*')):
  if f.is_file()and f.name not in service:
   b=f.read_bytes();inventory.append({'sku':sku,'path':str(f.relative_to(R)),'member':str(f.relative_to(source)),'sha256':sha(b),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()})
assert len(inventory)==172
for f in manifest:
 p=Q/'candidates'/f['path'];assert sha(p.read_bytes())==f['sha256']
 assert sha((R/f['path']).read_bytes())==f.get('base_sha256',f.get('source_sha256'))
 dest=Q/'package-sources'/f['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
seed=R.parents[2]/'tools/nsp-product-audit-fixes-20261021/remaining-review-20261022'
assert seed.is_dir(),seed
holds=[]
for p in sorted((seed/'candidates').rglob('*')):
 if p.is_file():holds.append({'path':str(p.relative_to(seed/'candidates')),'sha256':sha(p.read_bytes()),'status':'UNACCEPTED_NATIVE_OFFICE_BLOCKED','included_in_buyer_archives':False})
assert len(holds)==6
for f in protected:assert sha((Q/'package-sources'/f['path']).read_bytes())==f['accepted_sha256']
free=json.loads((Q/'free-docx-manifest.json').read_text())
for f in free:
 p=Q/'candidates'/f['path'];assert sha(p.read_bytes())==f['sha256']
 with ZipFile(R/f['archive'])as z:assert sha(z.read(f['member']))==f['base_sha256']
(Q/'SOURCE_INVENTORY.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2));(Q/'HELD_SIX.json').write_text(json.dumps(holds,ensure_ascii=False,indent=2));(Q/'PAID_CANDIDATE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(Q/'product-map.json').write_text(json.dumps(products,ensure_ascii=False,indent=2))
print('SOURCE_AND_CANDIDATE_VERIFIED',len(inventory),len(manifest),'PROTECTED',len(protected),'HELD',len(holds))
