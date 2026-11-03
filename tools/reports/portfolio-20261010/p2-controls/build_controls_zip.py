import argparse,hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parent;a=argparse.ArgumentParser();a.add_argument('base_zip',type=Path);args=a.parse_args();base=args.base_zip
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(base.read_bytes())=='cb3aae752db4bed41cbc0493997135021f00b2570f88d7a72f7c10650d08d5a4'
out=root/'P2_CONTROLS_CANDIDATE_2026-10-10.zip';members=[]
with zipfile.ZipFile(base) as src,zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as dst:
 for name in sorted(src.namelist()):
  old=src.read(name);new=(root/name).read_bytes() if name in ['07-raschet-stoimosti.xlsx','08-zhurnal-doprabot.xlsx'] else old
  info=zipfile.ZipInfo(name,(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;dst.writestr(info,new)
  members.append({'name':name,'sha256':sha(new),'bytes':len(new),'changed_from_route_a':new!=old})
with zipfile.ZipFile(out) as z:
 assert len(z.namelist())==15;assert z.testzip() is None
 for m in members:assert sha(z.read(m['name']))==m['sha256']
assert sum(m['changed_from_route_a'] for m in members)==2
receipt={'decision_id':'MB001-PRICE-PORTFOLIO-2026-10-10','target_name':'Система оформления и получения оплаты за дополнительные работы','target_price_rub':24900,'source_commit':'96c674f676fbdfbdec02f43977ae6c2961e25106','source_route_a_zip_sha256':sha(base.read_bytes()),'zip':out.name,'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size,'members':members,'status':'CANDIDATE_NOT_PRODUCT_OR_RELEASE_ACCEPTED','open_gates':['numeric input stop validation','sheet formula protection','native UI typed/paste validation','print setup and native A4 QA','full normative and independent buyer acceptance','target name and gated commercial release']}
(root/'receipt-controls.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print(receipt['sha256'],receipt['bytes'])
