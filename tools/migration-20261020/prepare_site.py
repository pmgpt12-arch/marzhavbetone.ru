#!/usr/bin/env python3
"""Prepare current published source for migration; buyer files stay byte-identical."""
from __future__ import annotations
import hashlib,importlib.util,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DIR=Path(__file__).resolve().parent
OUT=DIR/'evidence'
C=json.loads((DIR/'contract.json').read_text())
BASE=C['approved_base_commit']
VISUAL='79018043dd965313b73036f760572b0aaf77f9bd'
OLD='https://marzhavbetone.ru';NEW='https://nastoronepodryadchika.ru'
URL=re.compile(r'https?://(?:www\.)?marzhavbetone\.ru(?=[/\s"\'<>?#:]|$)')
HTML_DIRS={'products','articles','materialy','demo'}
PROTECTED=re.compile(r'(?:data-(?:sku|price|product)|id)=["\'][^"\']+["\']')
BUYER_REJECT_PREFIX=('products-storage/','orders/')

def run(args,timeout=60):
    return subprocess.run(args,cwd=ROOT,check=True,text=True,capture_output=True,timeout=timeout)
def git(*args):return run(['git',*args]).stdout
def write(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def current_products():
    spec=importlib.util.spec_from_file_location('nsp_inspect',DIR/'inspect_backup.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.repo_manifest()
def identity(text):
    return text.replace('Маржи в бетоне','На стороне подрядчика').replace('Маржа в бетоне','На стороне подрядчика').replace('маржа в бетоне','на стороне подрядчика')
def approved_copy(text,rel):
    text=identity(text)
    text=re.sub(r'(<span\s+class="brand-mark">)М(</span>)',r'\g<1>Н\g<2>',text)
    text=re.sub(r'(<a\b[^>]*href="/?articles/"[^>]*>)Разборы(</a>)',r'\g<1>Практика и судебные решения\g<2>',text)
    text=text.replace('"name": "Разборы"','"name": "Практика и судебные решения"')
    text=text.replace('Новые разборы — в канале и в Дзене','Новые материалы — в Telegram и Дзене')
    if rel=='index.html':
        replacements={
         'ДЛЯ СТРОИТЕЛЬНЫХ ПОДРЯДЧИКОВ И СУБПОДРЯДЧИКОВ':'ДЛЯ ИСПОЛНИТЕЛЕЙ РАБОТ И УСЛУГ В СТРОИТЕЛЬСТВЕ',
         '<h1>Система получения оплаты <em>за выполненные строительные работы</em></h1>':'<h1>Практические системы <em>для решения спорных вопросов с заказчиком</em></h1>',
         'Готовые алгоритмы и документы для каждого этапа: договор, допработы, исполнительная документация, КС-2 и КС-3, удержания и получение оплаты.':'Готовые комплекты документов, расчёты и пошаговые алгоритмы действий — от согласования условий договора и дополнительных работ до приёмки результата, оспаривания удержаний и получения оплаты.',
         '<a class="button" href="#situations">Выбрать свою ситуацию</a>':'<a class="button" href="#situations">Подобрать решение под свою ситуацию →</a>',
         'Работы закрыты, но денег нет':'Результат принят, оплата задерживается',
         'КС подписаны, срок оплаты прошёл или заказчик откладывает расчёт.':'Приёмка результата работ или услуг подтверждена, срок оплаты прошёл либо заказчик переносит расчёт.',
         'СВЕЖИЕ РАЗБОРЫ':'ПРАКТИКА И СУДЕБНЫЕ РЕШЕНИЯ',
         'Все разборы →':'Все материалы →','Витрина разборов →':'Смотреть практические материалы →','Открыть разбор →':'Читать материал →',
        }
        for old,new in replacements.items():text=text.replace(old,new)
        assert 'Практические системы <em>для решения спорных вопросов с заказчиком</em>' in text,'APPROVED_HERO_NOT_APPLIED'
    if rel=='articles/index.html':
        text=text.replace('Разборы — На стороне подрядчика','Практика и судебные решения — На стороне подрядчика')
        text=text.replace('<li aria-current="page">Разборы</li>','<li aria-current="page">Практика и судебные решения</li>')
        text=text.replace('<h1>Деньги теряются тихо</h1>','<h1>Практика и судебные решения</h1>')
        text=text.replace('ВИТРИНА ЭКСПЕРТИЗЫ','ПРАКТИЧЕСКИЕ МАТЕРИАЛЫ').replace('Темы разборов','Темы практических материалов')
        text=text.replace('Разборы для строительных подрядчиков','Практические материалы для исполнителей работ и услуг в строительстве')
    return text

def main():
    checkpoint=json.loads((OUT/'checkpoint.json').read_text())
    assert checkpoint['status']=='PASS_INSPECT_PRIVATE_BACKUPS_FULL_13SKU_MANIFEST' and checkpoint['source_main']==BASE
    run(['git','fetch','--no-tags','--depth=1','origin','main'])
    assert git('rev-parse','FETCH_HEAD').strip()==BASE,'MAIN_ADVANCED_BEFORE_PREPARATION'
    source=json.loads((OUT/'repository-full-13sku-manifest.json').read_text())['products']
    assert current_products()==source,'SOURCE_PORTFOLIO_DRIFT_BEFORE_PREPARATION'
    run(['git','fetch','--no-tags','--depth=1','origin',VISUAL])
    for rel in ['brand-approved-2026.css','favicon.svg','favicon-32.png','favicon.ico','apple-touch-icon.png']:
        data=subprocess.run(['git','show',VISUAL+':'+rel],cwd=ROOT,check=True,capture_output=True,timeout=25).stdout
        (ROOT/rel).write_bytes(data)
    version=hashlib.sha1((ROOT/'brand-approved-2026.css').read_bytes()).hexdigest()[:8]
    tracked=git('ls-files').splitlines()
    pages=[p for p in tracked if p.endswith('.html') and (len(Path(p).parts)==1 or Path(p).parts[0] in HTML_DIRS)]
    assert len(pages)>=80,'PUBLIC_PAGE_SCOPE_UNEXPECTED'
    before_attrs={p:PROTECTED.findall((ROOT/p).read_text()) for p in pages}
    changes=[]
    for rel in pages:
        path=ROOT/rel;original=path.read_text(encoding='utf-8')
        text=URL.sub(NEW,approved_copy(original,rel))
        match=re.search(r'<body\b[^>]*>',text,re.I);assert match,'BODY_MISSING_'+rel
        tag=match.group(0)
        if 'rebrand-approved' not in tag:
            if 'class="' in tag:tag=tag.replace('class="','class="rebrand-approved ',1)
            else:tag=tag[:-1]+' class="rebrand-approved">'
            text=text[:match.start()]+tag+text[match.end():]
        if 'brand-approved-2026.css' not in text:
            links=list(re.finditer(r'<link\b[^>]*rel="stylesheet"[^>]*>',text[:text.lower().index('</head>')],re.I))
            assert links,'STYLESHEET_ANCHOR_MISSING_'+rel
            prefix='../'*(len(Path(rel).parts)-1);pos=links[-1].end()
            text=text[:pos]+f'\n  <link rel="stylesheet" href="{prefix}brand-approved-2026.css?v={version}">'+text[pos:]
        assert PROTECTED.findall(text)==before_attrs[rel],'PRODUCT_OR_DOM_IDENTIFIERS_CHANGED_'+rel
        path.write_text(text,encoding='utf-8')
        if text!=original:changes.append(rel)
    for rel in ['data/site/navigation.yaml','tools/build_sitemap.py','tools/build_rss.py','tools/link_audit.py']:
        p=ROOT/rel;s=p.read_text();t=URL.sub(NEW,identity(s))
        if rel.endswith('navigation.yaml'):
            t=t.replace('  mark: М','  mark: Н').replace('    text: Разборы\n    href: /articles/','    text: Практика и судебные решения\n    href: /articles/')
        if rel.endswith('build_rss.py'):
            t=t.replace('Разборы для строительных подрядчиков:','Практические материалы для исполнителей работ и услуг в строительстве:')
        p.write_text(t);changes.append(rel)
    for rel in ['robots.txt','sitemap.xml','config.php']:
        p=ROOT/rel;s=p.read_text();t=URL.sub(NEW,s)
        if rel=='robots.txt':t=t.replace('Host: marzhavbetone.ru','Host: nastoronepodryadchika.ru')
        p.write_text(t);changes.append(rel)
    p=ROOT/'products-config.php';s=p.read_text();t=s.replace('«Маржа в бетоне»','«На стороне подрядчика»')
    assert t.replace('«На стороне подрядчика»','«Маржа в бетоне»')==s,'UNEXPECTED_EMAIL_CODE_DELTA'
    p.write_text(t);changes.append('products-config.php')
    p=ROOT/'.htaccess';s=p.read_text();t=URL.sub(NEW,s).replace('www\\.marzhavbetone\\.ru','www\\.nastoronepodryadchika\\.ru')
    t=t.replace('    RewriteRule ^(.*)$ '+NEW+'/$1 [R=301,L]', '    RewriteCond %{REQUEST_METHOD} ^(?:GET|HEAD)$\n    RewriteRule ^(.*)$ '+NEW+'/$1 [R=301,L]')
    harden='''# Migration protection: includes work internally, direct HTTP access is denied.
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule ^(?:orders|products-storage|delivery|tools|content|\\.git)(/|$) - [F,L]
    RewriteRule ^(?:config\\.php(?:\\..*)?|products-config\\.php|.*\\.(?:bak|sql|tar|tgz))$ - [F,L,NC]
</IfModule>
'''
    p.write_text((harden+'\n'+t).rstrip()+'\n');changes.append('.htaccess')
    for args in [['python3','tools/build_nav.py','--write'],['python3','tools/asset_versions.py','--write'],['python3','tools/build_sitemap.py','--verify'],['python3','tools/build_rss.py'],['python3','tools/check_nav.py'],['python3','tools/link_audit.py','--verify'],['php','tools/test_price_authority.php'],['php','tools/test_delivery_one_hour.php']]:run(args)
    assert current_products()==source,'BUYER_FILES_OR_SERVER_CATALOG_CHANGED'
    for rel in ['payment.php','webhook.php','check-payment.php','download.php']:
        assert (ROOT/rel).read_bytes()==subprocess.run(['git','show',BASE+':'+rel],cwd=ROOT,check=True,capture_output=True).stdout,'PAYMENT_HANDLER_CHANGED_'+rel
    shipping=[]
    for rel in sorted(set(tracked)|{'brand-approved-2026.css','rss.xml'}):
        p=ROOT/rel
        if not p.is_file() or rel=='config.php':continue
        parts=Path(rel).parts
        allowed=(len(parts)==1 and (p.suffix.lower() in {'.html','.css','.js','.svg','.ico','.png','.jpg','.xml','.txt','.php','.webmanifest'} or rel=='.htaccess')) or parts[0] in HTML_DIRS|{'assets'}
        if not allowed:continue
        assert not rel.startswith(BUYER_REJECT_PREFIX)
        shipping.append({'file':rel,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    assert any(x['file']=='index.html' for x in shipping) and not any(x['file']=='config.php' for x in shipping)
    old_ht=subprocess.run(['git','show',BASE+':.htaccess'],cwd=ROOT,check=True,capture_output=True,text=True).stdout
    old_route='''# Preserve POST handlers: no HTTP redirect for payment, webhook, status or download.
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule ^(?:orders|products-storage|delivery|tools|content|\\.git)(/|$) - [F,L]
    RewriteRule ^(?:config\\.php(?:\\..*)?|products-config\\.php|.*\\.(?:bak|sql|tar|tgz))$ - [F,L,NC]
    RewriteRule ^\\.well-known/acme-challenge/ - [L]
    RewriteRule ^(?:payment|webhook|check-payment|download|contact)\\.php$ - [L]
    RewriteCond %{REQUEST_METHOD} ^(?:GET|HEAD)$
    RewriteRule ^ https://nastoronepodryadchika.ru%{REQUEST_URI} [R=301,L,NE]
</IfModule>
'''
    generated=(old_route+'\n'+old_ht).rstrip()+'\n'
    assert not generated.endswith('\n\n'),'GENERATED_TEMPLATE_EXTRA_EOF_LINE'
    (DIR/'old-domain-cutover.htaccess').write_text(generated)
    plan={'status':'PASS_PREPARED_FROM_PUBLISHED_MAIN','source_main':BASE,'approved_style_source':VISUAL,'new_domain':C['new_domain'],'shipping_files':shipping,'do_not_ship':['config.php','products-storage/','orders/'],'config_strategy':'derive private live copy; set SITE_URL=new; retain absolute existing masters/orders/delivery; never print credentials','old_handlers_strategy':'PHP include bridge to new handlers; shared absolute ORDERS_DIR; no ordinary 301 for payment POST','buyer_manifest_preserved':True,'buyer_files':172,'active_skus':13,'support_email_unchanged':C['support_email_preserve_until_verified'],'sender':'retain authenticated site@marzhavbetone.ru until new sender is verified','main_changed':False,'public_pages':len(pages),'new_root_initial_mode':'stage with temporary noindex before owner real payment and final redirects','cutover_not_executed':True}
    write('prepared-site-plan.json',plan)
    assert (ROOT/C['existing_check_classification']).read_bytes()==subprocess.run(['git','show',BASE+':'+C['existing_check_classification']],cwd=ROOT,check=True,capture_output=True).stdout
    write('prepare-checkpoint.json',{'status':'PASS_SOURCE_AND_PRICE_DOCUMENT_INVARIANTS','source_main':BASE,'public_pages':len(pages),'shipping_count':len(shipping),'sku_count':13,'buyer_files':172,'payment_handler_sha_unchanged':True,'p1_catalog_and_masters_unchanged':True,'prod_touched':False,'next':'remote scoped dry-run and isolated new-root staging'})
    print('PREPARED_CURRENT_MAIN 13_SKUS 172_UNCHANGED_BUYER_FILES',flush=True)

if __name__=='__main__':main()
