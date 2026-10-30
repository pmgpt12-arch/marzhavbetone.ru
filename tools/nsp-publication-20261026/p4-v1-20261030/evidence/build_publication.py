from pathlib import Path
import json,base64,hashlib,re,shutil,subprocess
from html import escape
D=Path('/home/denis/projects/nsp-qa16-p4-20261030/publication');B=D/'snapshot';T=D/'current-only';assert not T.exists();H=lambda b:hashlib.sha256(b).hexdigest();SHA='a581a2174e65184573fb56747431fd8afd37862ef418a84ffa613d1a630b05ea'
r=json.loads((D/'SNAPSHOT_REQUEST.json').read_text());PREFIX=r['prefix'];pagepath=r['page'];snap=json.loads((B/'p4-production-snapshot.json').read_text())
for n,row in snap['files'].items():
 b=base64.b64decode(row['base64']);assert H(b)==row['sha256'];p=B/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
members=json.loads((D/PREFIX/'REVIEW_MANIFEST.json').read_text())['files'];assert len(members)==26 and H((D/'current.zip').read_bytes())==SHA
T.mkdir();(T/'pages/products').mkdir(parents=True);shutil.copyfile(D/'current.zip',T/'current.zip')
page=(B/pagepath).read_text();page=page.replace('25 файлов, включая инструкции','26 файлов: 13 DOCX, 6 XLSX и 7 PDF. Одна PDF-инструкция').replace('25 файлов','26 файлов').replace('00-START-HERE.txt','00-INSTRUKCIYA.pdf').replace('<h3>Порядок начала работы</h3>','<h3>PDF-инструкция по комплекту</h3>')
new='<article class="doc-item"><h3>Редактируемый рабочий акт скрытых работ</h3><p><code style="overflow-wrap:anywhere">31A-rabochiy-akt-skrytyh-rabot.docx</code></p><p>Рабочая форма. Реквизиты и состав участников сверяйте с требованиями объекта; исходный нормативный PDF приведён отдельно.</p></article>\n'
anchor='<article class="doc-item"><h3>Карточка исполнительной схемы</h3>';assert page.count(anchor)==1;page=page.replace(anchor,new+anchor,1)
assert 'data-sku="p4"'in page and 'В разработке'not in page
assert 'В разработке'not in page and set(re.findall(r'<code[^>]*>([^<]+)</code>',page))=={x['name']for x in members}
# Preserve Product metadata and add the actual offer to the newly available product.
pat=r'(<script type="application/ld\+json">)(.*?)(</script>)'
def offer(m):
 x=json.loads(m[2])
 if x.get('@type')=='Product':x['offers']={'@type':'Offer','priceCurrency':'RUB','price':'24900','availability':'https://schema.org/InStock','url':'https://nastoronepodryadchika.ru/'+pagepath}
 return m[1]+json.dumps(x,ensure_ascii=False,indent=2)+m[3]
page=re.sub(pat,offer,page,flags=re.S);(T/'pages'/pagepath).write_text(page)
cat=(B/'katalog.html').read_text();cards=[x for x in re.findall(r'<article\b[^>]*>.*?</article>',cat,re.S)if 'data-sku="p4"'in x];assert len(cards)==1
newcard=cards[0].replace('25 файлов, включая инструкции.','26 файлов: 13 DOCX, 6 XLSX и 7 PDF. Одна PDF-инструкция.');assert newcard!=cards[0];cat=cat.replace(cards[0],newcard,1)
assert cat.replace(newcard,cards[0],1)==(B/'katalog.html').read_text();(T/'pages/katalog.html').write_text(cat)
config=(B/'products-config.php').read_text()
a="""    if ($sku === 'p2' || $sku === 'p3') {
        $approved = $sku === 'p2'
            ? '42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da'
            : '54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b';
        $master = PRODUCTS_DIR . ($sku === 'p2' ? '/P2-v13-current.zip' : '/P3-v1-current.zip');"""
b="""    if ($sku === 'p2' || $sku === 'p3' || $sku === 'p4') {
        $current = [
            'p2' => ['42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da', '/P2-v13-current.zip'],
            'p3' => ['54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b', '/P3-v1-current.zip'],
            'p4' => ['SHA', '/P4-v1-current.zip'],
        ];
        [$approved, $currentMaster] = $current[$sku];
        $master = PRODUCTS_DIR . $currentMaster;""".replace('SHA',SHA)
assert config.count(a)==1;config=config.replace(a,b,1);(T/'pages/products-config.php').write_text(config)
m={'sku':'p4','edition':'P4-layout-v1','archive_sha256':SHA,'members':members,'old_members':{x['name']:x['sha256']for x in snap['product_locations'][0]['p4_files']},'pages':{n:{'before':snap['files'][n]['sha256'],'after':H((T/'pages'/n).read_bytes())}for n in [pagepath,'katalog.html','products-config.php']},'protected':{n:snap['files'][n]['sha256']for n in ['payment.php','download.php','app.js','app-script.php']},'delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY','owner_approval_commit':r['commit']}
(T/'release.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
php=Path('/home/denis/projects/nsp-qa15-p3-20261030/publication/current-only/publish.php').read_text().replace('54854b79366598cba9680c5c71451220a5de45929ff33bcf42eba9b97dbcb92b',SHA).replace('p3-shablony-ks2-ks3','p4-ispolnitelnaya-dokumentaciya-pto').replace('P3','P4').replace('p3','p4').replace('05-ks-bez-vozvrata','08-pto-bez-zamechaniy').replace('1790000','2490000').replace('!==11','!==26').replace('=>11','=>26')
(T/'publish.php').write_text(php)
for p in [T/'publish.php',T/'pages/products-config.php']:subprocess.run(['php','-l',str(p)],capture_output=True,check=True,timeout=8)
print(json.dumps({'status':'P4_RELEASE_PREPARED','members':26,'manifest_sha256':H((T/'release.json').read_bytes())}))
