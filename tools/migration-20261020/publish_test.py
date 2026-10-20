#!/usr/bin/env python3
"""Publish disabled-commerce acceptance copy; verify real HTTPS and ZIP contents.
No real payment or email is claimed. Roll back new root on any failed gate.
"""
from __future__ import annotations
import base64,hashlib,io,json,os,sys,urllib.error,urllib.parse,urllib.request,zipfile
from html.parser import HTMLParser
from pathlib import Path
import inspect_backup as inspection
from dry_run_new import run,ssh_args
from legacy_http_gate import verify as verify_legacy_html, self_test as test_legacy_gate

ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent
OUT=D/'evidence'
LIMIT=30*1024*1024


def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


class Canonical(HTMLParser):
    def __init__(self,text):
        super().__init__();self.url=None;self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='link' and a.get('rel')=='canonical':self.url=a.get('href')


def http(url,label,method='GET',body=None):
    try:
        request=urllib.request.Request(url,data=body,method=method,
          headers={'User-Agent':'NSP-Migration-Acceptance/1.0','Cache-Control':'no-cache','Content-Type':'application/json'})
        try:response=urllib.request.urlopen(request,timeout=15)
        except urllib.error.HTTPError as exc:response=exc
        with response:
            data=response.read(LIMIT+1)
            assert len(data)<=LIMIT,'HTTP_SIZE_BUDGET:'+label
            return response.code,data,{k.lower():v for k,v in response.headers.items()},response.url
    except (urllib.error.URLError,OSError,TimeoutError) as exc:
        # Never put tokenized download URLs or response bodies in an exception.
        raise RuntimeError('HTTP_TRANSPORT:'+label+':'+type(exc).__name__) from None


def prepare():
    c=json.loads((D/'contract.json').read_text())
    stage=json.loads((OUT/'private-stage-verification.json').read_text())
    baseline=json.loads((OUT/'dry-run-live-inspection.json').read_text())
    host=json.loads((OUT/'new-root-host-plan.json').read_text())
    plan=json.loads((OUT/'prepared-site-plan.json').read_text())
    assert stage['status']=='PASS_PRIVATE_HOST_CANDIDATE_AND_13_ARCHIVES'
    assert stage['active_skus']==13 and stage['buyer_files']==172 and stage['credentials']=='DUMMY_DISABLED_NO_LIVE_SECRETS'
    payload={'paths':baseline['paths'],'workspace':stage['workspace'],'new_domain':c['new_domain'],
      'original_new_tree_sha256':host['new_root_tree_sha256'],'shipping':plan['shipping_files'],
      'old_code_sha256':baseline['code_sha256'],'old_config_sha256':baseline['config_sha256_not_contents']}
    script=(D/'publish_test.php').read_text();assert script.count('__PAYLOAD__')==1
    script=script.replace('__PAYLOAD__',base64.b64encode(json.dumps(payload).encode()).decode())
    def remote(phase):
        assert phase in {'publish','links','expire','rollback'}
        host=os.environ['USER']+'@'+os.environ['HOST']
        result=run([*ssh_args(),host,'php -f /dev/stdin -- '+phase],180,input=script,text=True)
        return json.loads(result.stdout)
    return c,stage,baseline,plan,remote


def main():
    c,stage,baseline,plan,remote=prepare()
    if '--rollback-only' in sys.argv:
        receipt=remote('rollback');write('new-domain-test-rollback.json',receipt)
        print('ROLLBACK_CHECK',receipt['status'],flush=True);return
    run(['git','fetch','--no-tags','--depth=1','origin','main'],45,text=True)
    assert run(['git','rev-parse','FETCH_HEAD'],text=True).stdout.strip()==c['approved_base_commit'],'MAIN_ADVANCED'
    accepted=json.loads((OUT/'repository-full-13sku-manifest.json').read_text())['products']
    assert inspection.repo_manifest()==accepted,'SOURCE_MASTER_DRIFT'
    for item in plan['shipping_files']:
        assert hashlib.sha256((ROOT/item['file']).read_bytes()).hexdigest()==item['sha256'],'SHIPPING_HASH_DRIFT'
    before=inspection.remote('inspect')
    for key in ['paths','products','code_sha256','config_sha256_not_contents','new_root_index_sha256']:
        assert before[key]==baseline[key],'LIVE_STATE_CHANGED:'+key
    assert not before['runtime']['new_config_exists'],'NEW_ROOT_ALREADY_CONFIGURED'
    # Fail before touching either public root if CDN normalization regresses.
    old_source=run(['git','show',c['approved_base_commit']+':index.html'],20).stdout
    assert hashlib.sha256(old_source).hexdigest()==baseline['code_sha256']['index.html'],'LEGACY_ORIGIN_SOURCE_CHANGED'
    test_legacy_gate(old_source)
    attempts=False
    report={'status':'RUNNING_NEW_DOMAIN_ACCEPTANCE','run':os.environ['GITHUB_RUN_ID'],
      'source_main':c['approved_base_commit'],'old_store_modified':False,
      'real_payment':False,'emails_sent':0,'payment_endpoints_enabled':False,
      'pages':[],'security':[],'downloads':[],'expired_links':[]}
    try:
        attempts=True
        publication=remote('publish');write('new-domain-test-publication.json',publication)
        assert publication['status']=='PASS_PUBLISHED_NEW_DOMAIN_TEST_MODE'
        base='https://'+c['new_domain']
        browser=json.loads((OUT/'browser-candidate.json').read_text())
        selected=browser['sku_pages'];assert set(selected)==set(accepted),'ACTIVE_PRODUCT_PAGE_MAP_DRIFT'
        targets=['index.html','katalog.html','diagnostika.html','articles/index.html','materialy/index.html',*selected.values()]
        for rel in targets:
            code,data,headers,final=http(base+'/'+rel,'PAGE:'+rel)
            text=data.decode('utf-8','replace')
            assert code==200 and urllib.parse.urlsplit(final).hostname==c['new_domain'],('PAGE_HTTP',rel,code)
            assert 'data-nsp-staging="true"' in text and 'noindex' in headers.get('x-robots-tag',''),('STAGING_GUARDS',rel)
            expected_canonical=Canonical((ROOT/rel).read_text()).url
            assert Canonical(text).url==expected_canonical and expected_canonical.startswith(base),('CANONICAL',rel)
            assert 'На стороне подрядчика' in text and 'Практика и судебные решения' in text,('BRAND_NAV',rel)
            report['pages'].append({'path':rel,'http':code,'canonical':expected_canonical,'stage_noindex':True,'sha256':hashlib.sha256(data).hexdigest()})
        for url in ['https://www.'+c['new_domain']+'/?utm_source=migration-check',
                    'http://'+c['new_domain']+'/?utm_source=migration-check',
                    'http://www.'+c['new_domain']+'/?utm_source=migration-check']:
            code,data,headers,final=http(url,'HOST_VARIANT')
            parts=urllib.parse.urlsplit(final)
            assert code==200 and parts.scheme=='https' and parts.hostname==c['new_domain'],'HOST_VARIANT_LOOP_OR_WRONG_TARGET'
            assert urllib.parse.parse_qs(parts.query).get('utm_source')==['migration-check'],'HOST_REDIRECT_QUERY_LOST'
        for rel in ['config.php','config.php.bak','products-config.php','orders/','orders/delivery/',
                    'products-storage/','.git/HEAD','tools/migration-20261020/probe.php','delivery/']:
            code,data,headers,_=http(base+'/'+rel,'PRIVACY:'+rel)
            assert code in (403,404),('PRIVATE_PATH_EXPOSED',rel,code)
            assert b'<?php' not in data and b'YOOKASSA_SECRET_KEY' not in data and b'/var/www/' not in data,('SOURCE_LEAK',rel)
            report['security'].append({'path':rel,'http':code,'exposed':False})
        for rel in ['payment.php','webhook.php','check-payment.php','contact.php']:
            code,data,headers,_=http(base+'/'+rel,'DISABLED_POST:'+rel,method='POST',body=b'{}')
            assert code==503 and 'location' not in headers,('STAGING_POST_NOT_BLOCKED',rel,code)
            report['security'].append({'path':rel,'method':'POST','http':503,'redirect':False})
        code,robots,_,_=http(base+'/robots.txt','ROBOTS')
        assert code==200 and b'Disallow: /' in robots,'STAGE_ROBOTS'
        links=remote('links');assert set(links)==set(accepted),'PRIVATE_PROBE_SCOPE'
        for sku,spec in accepted.items():
            url=links[sku]['url'];parsed=urllib.parse.urlsplit(url)
            assert parsed.scheme=='https' and parsed.hostname==c['new_domain'] and parsed.path=='/download.php','PRIVATE_URL_SCOPE'
            code,data,headers,final=http(url,'DOWNLOAD:'+sku)
            assert code==200 and urllib.parse.urlsplit(final).hostname==c['new_domain'],('DOWNLOAD_HTTP',sku,code)
            assert 'application/zip' in headers.get('content-type',''),('DOWNLOAD_CONTENT_TYPE',sku)
            assert spec['zip'] in headers.get('content-disposition',''),('DOWNLOAD_FILENAME',sku)
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names=z.namelist();assert len(names)==len(set(names)) and set(names)==set(spec['files']),('ZIP_MEMBER_SET',sku)
                assert z.testzip() is None,('ZIP_CRC',sku)
                for name,meta in spec['files'].items():
                    assert z.getinfo(name).file_size==meta['size'],('ZIP_SIZE',sku,name)
                    content=z.read(name)
                    assert hashlib.sha256(content).hexdigest()==meta['sha256'],('ZIP_SHA',sku,name)
            report['downloads'].append({'sku':sku,'http':200,'files':len(names),'crc':'PASS',
              'all_member_sha256':'PASS','zip_sha256':hashlib.sha256(data).hexdigest(),'expected_filename':spec['zip'],
              'order_scenario':'SYNTHETIC_PAID_STATUS_NO_PROVIDER_TRANSACTION'})
            print('PASS_HTTP_ZIP',sku,len(names),'MEMBERS_SHA_AND_CRC',flush=True)
        first=next(iter(links.values()))['url'];parts=urllib.parse.urlsplit(first);query=urllib.parse.parse_qs(parts.query)
        query['t']=['0'*32]
        invalid=urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query,doseq=True)))
        code,_,_,_=http(invalid,'WRONG_TOKEN');assert code==403,'INVALID_TOKEN_NOT_REJECTED'
        expired=remote('expire');assert expired['orders']==13
        for sku,link in links.items():
            code,_,_,_=http(link['url'],'EXPIRED:'+sku)
            assert code==410,('EXPIRED_DOWNLOAD_HTTP',sku,code)
            report['expired_links'].append({'sku':sku,'http':410})
        after=inspection.remote('inspect')
        for key in ['paths','products','code_sha256','config_sha256_not_contents']:
            assert after[key]==before[key],'OLD_LIVE_STATE_CHANGED:'+key
        assert after['runtime']['new_config_exists']
        oldcode,oldbody,_,oldfinal=http('https://'+c['old_domain']+'/','OLD_STORE')
        assert oldcode==200 and urllib.parse.urlsplit(oldfinal).hostname==c['old_domain'],'OLD_STORE_REDIRECTED_PREMATURELY'
        old_verified=verify_legacy_html(oldbody,old_source)
        assert old_verified['expected_origin_sha256']==before['code_sha256']['index.html'],'OLD_STOREFRONT_CHANGED'
        report['old_store_http']={
          'status':old_verified['status'],
          'raw_http_sha256':old_verified['raw_http_sha256'],
          'normalized_sha256':old_verified['normalized_sha256'],
          'transformations':old_verified['transformations']
        }
        assert len(report['downloads'])==13 and sum(r['files'] for r in report['downloads'])==172
        report.update(status='PASS_NEW_DOMAIN_HTTPS_AND_13_SYNTHETIC_DOWNLOADS',
          buyer_files=172,active_skus=13,ttl_definition_seconds=3600,expired_http=410,
          old_store_serving_unchanged=True,real_orders_and_masters_untouched=True,
          new_site='https://'+c['new_domain']+'/',
          release_state='STAGING_ONLY_NOINDEX_PAYMENTS_DISABLED',
          payment_evidence='NO_REAL_PAYMENT_PERFORMED; synthetic order status tests delivery only',
          email_evidence='RENDERED_ONLY_NOT_SENT',
          expiry_scenario='Declared 3600 seconds checked at issue; each synthetic order expires_at set into past, HTTP 410 verified',
          remaining=['Enable vetted live config with shared production order/cache paths',
            'Verify actual provider payment and webhook plus delivered email on new host',
            'Activate ordinary old-host redirects only after real buyer acceptance',
            'Update permanent deployment target and remove temporary noindex/staging overlay'])
        write('new-domain-http-acceptance.json',report)
        print('PASS_NEW_DOMAIN_HTTP 13_ARCHIVES 172_FILES 13_EXPIRED_410 OLD_STORE_UNCHANGED PAYMENT_NOT_VERIFIED',flush=True)
    except Exception as exc:
        report.update(status='FAIL_NEW_DOMAIN_TEST',error=type(exc).__name__+':'+str(exc)[:1800])
        write('new-domain-http-acceptance.json',report)
        if attempts:
            try:
                rollback=remote('rollback');write('new-domain-test-rollback.json',rollback)
                print('ROLLBACK',rollback['status'],flush=True)
            except Exception as recovery:
                write('new-domain-test-rollback.json',{'status':'ROLLBACK_REQUIRES_ATTENTION','error':type(recovery).__name__+':'+str(recovery)[:1000]})
        raise


if __name__=='__main__':main()
