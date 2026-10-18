#!/usr/bin/env python3
"""Compare live T3 content while allowing Cloudflare email obfuscation in footers."""
from pathlib import Path
from bs4 import BeautifulSoup
import subprocess
files=['katalog.html','products/t3-odnostoronniy-akt-i-zachet.html','diagnostika.html','materialy/uderzhaniya.html','articles/garantiynoe-uderzhanie-v-ks-2-i-ks-3.html','articles/raboty-ne-prinyaty.html']
for n in files:
 data=subprocess.check_output(['curl','-fsSL','--max-time','20','-H','Cache-Control: no-cache','https://marzhavbetone.ru/'+n+'?t3_r2_http=39084501585'])
 live=BeautifulSoup(data,'html.parser');local=BeautifulSoup(Path(n).read_bytes(),'html.parser')
 # The web server source SHA was already checked by the release job.
 # Edge email obfuscation changes footer HTML; verify the product-bearing content.
 assert live.select_one('main').get_text(' ',strip=True)==local.select_one('main').get_text(' ',strip=True),'main text mismatch '+n
 sel=lambda s:[x.get_text() for x in s.select('script') if x.get('type')=='application/ld+json' or 'const SCENARIOS' in x.get_text()]
 assert sel(live)==sel(local),'T3 structured data mismatch '+n
 print(n+' HTTP_CONTENT_PASS')
