from pathlib import Path
import sys,json,hashlib,re,base64,shutil,subprocess,zipfile,copy
sys.path.insert(0,'/home/denis/projects/nsp-qa13-20261024')
from prepare_p1_publication_20261030 import D,api,fetch,commit,PREFIX,BR
H=lambda b:hashlib.sha256(b).hexdigest()
B=D/'snapshot';T=D/'current-only';assert not T.exists()
T.mkdir();(T/'pages/products').mkdir(parents=True)
A=Path('/home/denis/projects/nsp-qa13-20261024/owner-layout-review-20261029/QA13_P1_V1_18_FILES_NONRELEASE_20261029.zip')
SHA='99df41c33e25ce41b61b8e04e22e27871d08a2c383ddae234119a29df5f29ada'
assert H(A.read_bytes())==SHA
with zipfile.ZipFile(A)as z:
 assert z.testzip()is None and len(z.namelist())==18
 members=[{'name':n,'sha256':H(z.read(n)),'bytes':len(z.read(n))}for n in z.namelist()]
 assert sum(n['name'].startswith('00-')for n in members)==1
page=(B/'products/p1-oplata-po-ks2.html').read_text()
for old in ['00-INSTRUKCIYA.docx','00-START-HERE.txt']:
 pattern=r'<article class="doc-item"><h3>[^<]+</h3><p><code style="overflow-wrap:anywhere">'+re.escape(old)+r'</code></p></article>\s*'
 page,n=re.subn(pattern,'',page);assert n==1
page=page.replace('20 файлов','18 файлов')
page=page.replace('18 файлов, включая инструкции','18 файлов: 8 DOCX, 4 XLSX, 3 XLS и 3 PDF')
page=page.replace('18 файлов в одном архиве. Полный перечень:','18 файлов в одном архиве: 8 DOCX, 4 XLSX, 3 XLS и 3 PDF. Одна инструкция — 00-INSTRUKCIYA.pdf. Полный перечень:')
assert set(re.findall(r'<code[^>]*>([^<]+)</code>',page))=={m['name']for m in members}
assert len(re.findall(r'<code[^>]*>([^<]+)</code>',page))==18
(T/'pages/products/p1-oplata-po-ks2.html').write_text(page)
cat=(B/'katalog.html').read_text()
pattern=r'<article class="product-card" id="selection-oplata">.*?</article>'
cards=re.findall(pattern,cat,re.S);assert len(cards)==1
newcard=cards[0].replace('20 файлов, включая инструкции.','18 файлов: 8 DOCX, 4 XLSX, 3 XLS и 3 PDF.')
cat=cat.replace(cards[0],newcard,1)
description='Работы выполнены, но сдача документов или просроченная оплата задерживают поступление денег. Система связывает подтверждение объёмов, передачу документов и подготовку требования об оплате. 20 файлов, включая инструкции.'
assert cat.count(description)==1
cat=cat.replace(description,description.replace('20 файлов, включая инструкции.','18 файлов: 8 DOCX, 4 XLSX, 3 XLS и 3 PDF.'),1)
assert cat.replace(newcard,cards[0],1).replace(description.replace('20 файлов, включая инструкции.','18 файлов: 8 DOCX, 4 XLSX, 3 XLS и 3 PDF.'),description,1)==(B/'katalog.html').read_text()
(T/'pages/katalog.html').write_text(cat)
original=(B/'products-config.php').read_text()
start=original.index('/**\n * P1: неизменяемое издание.')
end=original.index('/** Без восстановления',start)
capture="""/** P1: текущее согласованное издание; один общий кеш, срок ссылки 3600 секунд. */
function mvb_capture_p1_edition(): ?array
{
    $sha = 'SHA_PLACEHOLDER';
    $edition = ['zip' => 'p1-' . $sha . '.zip', 'sha256' => $sha];
    $master = PRODUCTS_DIR . '/P1-v1-current.zip';
    if (!is_file($master) || !hash_equals($sha,(string)@hash_file('sha256',$master))) return null;
    $destination = DELIVERY_DIR . '/' . $edition['zip'];
    if (is_file($destination) && hash_equals($sha,(string)@hash_file('sha256',$destination))) return $edition;
    $stage = @tempnam(DELIVERY_DIR,'.p1-current-');
    if ($stage === false) return null;
    try {
        if (!copy($master,$stage) || !hash_equals($sha,(string)@hash_file('sha256',$stage))
            || !chmod($stage,0644) || !@rename($stage,$destination)) return null;
        return $edition;
    } finally { if (is_file($stage)) @unlink($stage); }
}

""".replace('SHA_PLACEHOLDER',SHA)
config=original[:start]+capture+original[end:]
needle="    $zipPath = DELIVERY_DIR . '/' . $catalog[$sku]['zip'];\n"
assert config.count(needle)==1
config=config.replace(needle,needle+"    if ($sku === 'p1') {\n        $edition = mvb_capture_p1_edition();\n        return $edition === null ? null : mvb_p1_edition_path($edition);\n    }\n",1)
assert config[config.index('function mvb_prepare_delivery'):]==original[original.index('function mvb_prepare_delivery'):]
(T/'pages/products-config.php').write_text(config)
snap=json.loads((B/'p1-production-snapshot.json').read_text())
m={'sku':'p1','edition':'P1-layout-v1','archive_sha256':SHA,'members':members,'old_members':{r['name']:r['sha256']for r in snap['product_locations'][0]['p1_files']},'pages':{n:{'before':snap['files'][n]['sha256'],'after':H((T/'pages'/n).read_bytes())}for n in ['products/p1-oplata-po-ks2.html','katalog.html','products-config.php']},'protected':{n:snap['files'][n]['sha256']for n in ['payment.php','download.php','app.js','app-script.php']},'delivery_policy':'NSP-DELIVERY-ONE-HOUR-CURRENT-ONLY','owner_approval_commit':json.loads((D/'SNAPSHOT_REQUEST.json').read_text())['commit']}
(T/'release.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(A,T/'current.zip')
# Adapt the already tested P2 current-files transaction to the actual P1 runtime.
php=Path('/home/denis/projects/nsp-qa14-20261024/p2-v13-publication-20261029/publish_current_files.php').read_text()
php=php.replace('42b67aeaa5a309b74ce0d396c31098c77832cc6d6235fd642e84bc0f6d4e71da',SHA).replace('P2','P1').replace('p2','p1').replace('02-dopraboty-bez-poter','01-zakrytie-rabot').replace('02-dopy-ne-v-podarok.zip','01-ks-podpisany-deneg-net.zip').replace('p1-dopolnitelnye-raboty','p1-oplata-po-ks2').replace('2490000','2990000').replace('!==13','!==18').replace("=>13","=>18").replace('v13','v1')
php=php.replace("$cache=$delivery.'/'.$p['zip'];","$cache=$delivery.'/p1-'.$sha.'.zip';\n$master=$root.'/P1-v1-current.zip';")
php=php.replace("['products/p1-oplata-po-ks2.html','katalog.html']","['products/p1-oplata-po-ks2.html','katalog.html','products-config.php']")
php=php.replace("if(inventory($source)!==$expected || !hash_ok($cache,$sha))","if(inventory($source)!==$expected || !hash_ok($cache,$sha) || !hash_ok($master,$sha))")
php=php.replace("$built=mvb_build_product_zip('p1');clearstatcache();","$edition=mvb_capture_p1_edition();\n    if(!is_array($edition)||$edition['sha256']!==$sha||mvb_p1_edition_path($edition)!==$cache)throw new RuntimeException('EDITION_BINDING');\n    $built=mvb_build_product_zip('p1');clearstatcache();")
# On apply the old config is already loaded; verify is intentionally a fresh CLI invocation.
php=php.replace('echo json_encode(verify_current()),"\\n";exit;\n}', 'echo json_encode([\'status\'=>\'P1_APPLIED_PENDING_FRESH_VERIFY\']),"\\n";exit;\n}',1)
anchor="$state['cache_written']=true;file_put_contents($journal,json_encode($state));"
assert php.count(anchor)==1
php=php.replace(anchor,anchor+"\n    if(file_exists($master))throw new RuntimeException('MASTER_ALREADY_PRESENT');\n    if(!copy($stage.'/current.zip',$master)||!hash_ok($master,$sha))throw new RuntimeException('MASTER_COPY');\n    chmod($master,0644);",1)
php=php.replace("if($state['source_swapped']){","if(is_file($master)&&hash_ok($master,$sha))unlink($master);\n    if($state['source_swapped']){",1)
# Capture exact old cache candidates before modifying; remove them only after verification.
anchor="$state=['source_swapped'=>false,'cache_written'=>false,'pages'=>[],'had_cache'=>is_file($cache)];"
assert php.count(anchor)==1
php=php.replace(anchor,anchor+"\n    $state['old_caches']=[];foreach(array_merge(glob($delivery.'/p1-*.zip')?:[],[$delivery.'/'.$p['zip']])as $file){if(is_file($file)&&$file!==$cache)$state['old_caches'][$file]=hash_file('sha256',$file);}",1)
anchor="$result=verify_current();clear_exact_dir($old,$before);"
assert php.count(anchor)==1
php=php.replace(anchor,"$result=verify_current();\n    $state=json_decode((string)file_get_contents($journal),true);\n    foreach($state['old_caches']as $file=>$expectedHash){if(is_file($file)){if(!hash_ok($file,$expectedHash))throw new RuntimeException('OLD_CACHE_CHANGED');if(!unlink($file))throw new RuntimeException('OLD_CACHE_CLEANUP');}}\n    clear_exact_dir($old,$before);",1)
php=php.replace('global $source,$cache,$sha,$expected,$pages,$site,$p;','global $source,$cache,$master,$sha,$expected,$pages,$site,$p;')
(T/'publish.php').write_text(php)
for p in [T/'publish.php',T/'pages/products-config.php']:
 subprocess.run(['php','-l',str(p)],check=True,capture_output=True,timeout=8)
for p in [T/'pages/products/p1-oplata-po-ks2.html',T/'pages/katalog.html']:
 for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>',p.read_text(),re.S):json.loads(s)
print(json.dumps({'status':'P1_CANDIDATE_PREPARED','manifest_sha256':H((T/'release.json').read_bytes()),'members':18,'html_member_count':18,'config_change':'Existing P1 capture returns exact approved current master; existing edition/download protocol retained'},ensure_ascii=False))
