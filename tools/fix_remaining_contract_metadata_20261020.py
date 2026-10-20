#!/usr/bin/env python3
from pathlib import Path
from hashlib import sha256
import json,shutil
R=Path(__file__).resolve().parents[1];O=R/'tools/candidates/remaining-batch-r3-20261018/release-20261020'
shutil.copyfile(O/'integration-check-classification.json',O/'integration-check-classification-before-contract-fix.json')
p=R/'articles/akty-skrytyh-rabot-kakie.html';before=p.read_bytes();text=before.decode();assert text.count('23 файла.')==1
text=text.replace('23 файла.','25 файлов.');p.write_text(text)
plan=json.loads((O/'release-plan.json').read_text());rel=str(p.relative_to(R));row=next((x for x in plan['site_files'] if x['file']==rel),None)
if row is None:
 row={'file':rel,'before_sha256':sha256(before).hexdigest()};plan['site_files'].append(row)
row['sha256']=sha256(p.read_bytes()).hexdigest();(O/'release-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
print('PASS exact P4 total count corrected in its linked article; buyer files unchanged')
