import hashlib, json, sys, zipfile
from pathlib import Path
p=Path(__file__).resolve().parent
source=Path(sys.argv[1])
assert hashlib.sha256(source.read_bytes()).hexdigest()=='1a709ad0b0e27f3bc367144a80cef5c292762c6e40b16e06ee8aab77aeabce11'
with zipfile.ZipFile(source) as z: items={n:z.read(n) for n in z.namelist()}
old=dict(items)
for filename in ['07-raschet-stoimosti.xlsx','08-zhurnal-doprabot.xlsx']:
    matches=[n for n in items if Path(n).name==filename]
    assert len(matches)==1
    items[matches[0]]=(p/filename).read_bytes()
archive=p/'P2_PRINT_CONTROLS_CANDIDATE_2026-10-10.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in items.items():
        info=zipfile.ZipInfo(name,(2026,10,10,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; z.writestr(info,data)
assert len(items)==15 and sum(items[n]!=old[n] for n in items)==2
receipt={'status':'CANDIDATE_NOT_RELEASE','decision':'MB001-PRICE-PORTFOLIO-2026-10-10','target_price_rub':24900,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'unchanged_members':13,'members':[{'path':n,'sha256':hashlib.sha256(b).hexdigest(),'changed':b!=old[n]} for n,b in items.items()]}
(p/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print(json.dumps({k:receipt[k] for k in ['sha256','bytes','unchanged_members']}))
