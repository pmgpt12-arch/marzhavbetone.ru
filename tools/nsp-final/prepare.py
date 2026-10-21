#!/usr/bin/env python3
"""Narrow corrections from the exact public production snapshot."""
import hashlib, json, re, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'tools/nsp-final/static-before.json'
REPLACEMENTS={
 'https://dzen.ru/marzhavbetone':'https://m.dzen.ru/nastoronepodryadchika',
 'https://t.me/marzhavbetone':'https://t.me/nastoronepodryadchika',
 'https://www.instagram.com/marzhavbetone/':'https://www.instagram.com/nastoronepodryadchika/',
 'https://instagram.com/marzhavbetone/':'https://www.instagram.com/nastoronepodryadchika/',
 'marzhavbetone@yandex.ru':'nastoronepodryadchika@yandex.ru',
}
BANNER=re.compile(r'<div data-nsp-staging="true"\b[^>]*>.*?</div>',re.S)

def corrected(text):
    for old,new in REPLACEMENTS.items(): text=text.replace(old,new)
    # Literal migration notice only; never alter other page content or robots rules.
    text=re.sub(r'<div data-nsp-staging="true"[^>]*>Проверочная версия нового сайта\..*?</div>','',text,flags=re.S)
    return text

def main():
    rows=json.loads(BASE.read_text()); manifest=[]
    for row in rows:
        p=ROOT/row['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'], 'SOURCE_DRIFT_'+row['path']
        if p.suffix in ['.html','.js']:
            data=corrected(p.read_bytes().decode('utf-8')).encode(); p.write_bytes(data)
    subprocess.run(['python3',str(ROOT/'tools/catalog_groups.py'),'--write'],check=True,cwd=ROOT)
    for row in rows:
        data=(ROOT/row['path']).read_bytes(); after=hashlib.sha256(data).hexdigest()
        if after!=row['sha256']: manifest.append({'path':row['path'],'before':row['sha256'],'after':after})
    (ROOT/'tools/nsp-final/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('TARGETED_FILES='+str(len(manifest)))

if __name__=='__main__': main()
