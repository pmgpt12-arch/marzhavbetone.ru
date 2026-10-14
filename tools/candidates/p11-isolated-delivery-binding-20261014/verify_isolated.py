#!/usr/bin/env python3
"""Synthetic offline full PHP delivery and download-handler checks.
Reads only pinned Git objects supplied by read(path). Creates and removes a private
TemporaryDirectory; no real mail, HTTP server, payment, source checkout or deployment.
"""
import base64, copy, hashlib, io, json, os, re, subprocess, tempfile, zipfile
from pathlib import Path

BASE='8311bb2dc7b497415952d03630e4a477f8bf9d7c'
PREFIX='tools/candidates/portfolio-owner-pdf-20261013/'
ARCHIVE=PREFIX+'p11-t6-consolidated-gold-20261014/p11-t6-eight-files-gold-candidate.zip'
LETTER=PREFIX+'19-kvartiry-vmesto-deneg/00-PISMO-POSLE-POKUPKI.txt'
ARCHIVE_SHA='f365039ef568dbbe9c661a6e1f553d21ddd0b086c9172f1e5a4340fb7dfe7f70'
LETTER_SHA='c8f9d78cf2335f2acf52ab8d12258e4e3e799c9c87e3447edcc17c7f0f507ea5'
EDITION={'kind':'p11-t6-gold-20261014','zip':'p11-'+ARCHIVE_SHA+'.zip','sha256':ARCHIVE_SHA,
         'letter':'p11-letter-'+LETTER_SHA+'.txt','letter_sha256':LETTER_SHA}
NAME='Система проверки расчётов недвижимостью и уступки прав'
EXPECTED_NAMES=['00-START-HERE.txt','50-slovar-poley-raschet-metrami.docx','51-algoritm-raschet-metrami.pdf',
'52-chek-list-raschet-metrami.docx','53-zapros-status-obekta.docx','54-zapros-sostoyanie-escrow.docx',
'55-pamyatka-punkt-ustupki-escrow.pdf','56-pervyy-den-do-podpisi.docx']

def sha(b): return hashlib.sha256(b).hexdigest()
def require(cond,label):
    if not cond: raise AssertionError(label)

def verify(read, build, helpers):
    inputs={n:read(n) for n in ['products-config.php','download.php']}
    accepted=read(ARCHIVE); letter=read(LETTER)
    require(sha(accepted)==ARCHIVE_SHA,'Accepted ZIP SHA')
    require(sha(letter)==LETTER_SHA,'Accepted letter SHA')
    outputs,patch=build(inputs,helpers)
    tests={}; downloads={}; messages={}
    def check(label,cond):
        require(cond,label); tests[label]='PASS'
    with tempfile.TemporaryDirectory(prefix='p11-binding-') as td:
        root=Path(td); os.chmod(root,0o700)
        src=root/'accepted'; src.mkdir()
        orders=root/'orders'; orders.mkdir(); delivery=orders/'delivery'; delivery.mkdir()
        masters=root/'masters'; masters.mkdir()
        (src/'accepted.zip').write_bytes(accepted); (src/'accepted-letter.txt').write_bytes(letter)
        for n,b in outputs.items(): (root/n).write_bytes(b)
        (root/'baseline.php').write_bytes(inputs['products-config.php'])
        conf="""<?php
declare(strict_types=1);
define('ORDERS_DIR', __DIR__.'/orders');
define('DELIVERY_DIR', __DIR__.'/orders/delivery');
define('PRODUCTS_DIR', __DIR__.'/masters');
define('SITE_URL', 'https://buyer-fixture.invalid');
define('ADMIN_EMAIL', 'support@fixture.invalid');
define('MVB_P11_CANDIDATE_SOURCE_DIR', __DIR__.'/accepted');
define('MVB_P11_CANDIDATE_BINDING', getenv('P11_ENABLED') !== '0');
"""
        (root/'config.php').write_text(conf)
        # Native mail is removed at PHP startup, then replaced solely by this recorder.
        bridge="""<?php
require __DIR__.'/config.php';
if (function_exists('mail')) throw new RuntimeException('Native mail must be disabled');
if (!function_exists('mail')) {
function mail($to,$subject,$body,$headers) {
    if (!str_ends_with((string)$to, '@fixture.invalid')) throw new RuntimeException('Non-synthetic recipient');
    file_put_contents(__DIR__.'/captured-mail.jsonl', json_encode(['to'=>$to,'subject'=>$subject,'body'=>$body],JSON_UNESCAPED_UNICODE)."\\n",FILE_APPEND);
    return true;
}
}
require __DIR__.'/'.(getenv('P11_BASELINE')==='1' ? 'baseline.php' : 'products-config.php');
$request=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR);
if ($request['op']==='catalog') { echo json_encode(mvb_products(),JSON_UNESCAPED_UNICODE); exit; }
$order=$request['order'];
if ($request['op']==='prepare') { $result=mvb_prepare_delivery($order); }
elseif ($request['op']==='notify') { $result=mvb_deliver_and_notify($order); }
else { throw new RuntimeException('Unknown fixture operation'); }
echo json_encode(['order'=>$order,'result'=>$result],JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
"""
        (root/'bridge.php').write_text(bridge)
        cli="""<?php
$_GET=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR);
register_shutdown_function(function(){file_put_contents(__DIR__.'/http-code.json',json_encode(['code'=>http_response_code()?:200]));});
require __DIR__.'/download.php';
"""
        (root/'download-cli.php').write_text(cli)
        php=['php','-d','disable_functions=mail,exec,shell_exec,system,passthru,popen,proc_open,curl_exec',
             '-d','allow_url_fopen=0','-d','display_errors=stderr','-d','open_basedir='+td,
             '-d','sys_temp_dir='+td]
        env={k:v for k,v in os.environ.items() if k not in ['PHPRC','PHP_INI_SCAN_DIR']}
        def run(file,payload,extra=None):
            e=env.copy(); e.update(extra or {})
            p=subprocess.run(php+[str(root/file)],input=json.dumps(payload,ensure_ascii=False).encode(),
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=root,env=e,timeout=8)
            require(p.returncode==0,f'PHP {file} exit {p.returncode}: '+p.stderr.decode(errors='replace'))
            require(not p.stderr,f'PHP warnings: '+p.stderr.decode(errors='replace'))
            return p.stdout
        def call(order,op='prepare',extra=None):
            return json.loads(run('bridge.php',{'op':op,'order':order},extra))
        def new(sku='p11',marked=True):
            item={'sku':sku}
            if marked:item['edition']=copy.deepcopy(EDITION)
            return {'id':'order_20261014_1_'+sku,'status':'paid','email':'buyer@fixture.invalid','items':[item]}
        def get(order,sku='p11',overrides=None):
            (orders/(order['id']+'.json')).write_text(json.dumps(order,ensure_ascii=False))
            q={'o':order['id'],'t':order['delivery']['token'],'f':sku};q.update(overrides or {})
            raw=run('download-cli.php',q)
            code=json.loads((root/'http-code.json').read_text())['code']
            saved=json.loads((orders/(order['id']+'.json')).read_text())
            return code,raw,saved
        for f in ['products-config.php','download.php','bridge.php','download-cli.php']:
            p=subprocess.run(php+['-l',str(root/f)],capture_output=True,timeout=5)
            check('php_lint_'+f,p.returncode==0)
        c1=json.loads(run('bridge.php',{'op':'catalog'}, {'P11_BASELINE':'1'}))
        c2=json.loads(run('bridge.php',{'op':'catalog'}))
        check('catalog_prices_sku_names_dirs_byte_equal',c1==c2)
        # Source drift prevents use of the overlay rather than guessing new anchors.
        bad=inputs.copy(); bad['products-config.php']+=b'\n'
        try:build(bad,helpers)
        except ValueError: check('stale_base_rejected',True)
        else:check('stale_base_rejected',False)
        first=new(); n=call(first,'notify'); issued=n['order']
        check('new_paid_order_prepared',len(n['result'])==1 and issued['delivery']['editions']['p11']==EDITION)
        check('new_name_only_in_binding',n['result'][0]['name']==NAME)
        mailpath=root/'captured-mail.jsonl'; mailrows=[json.loads(x) for x in mailpath.read_text().splitlines()]
        body=mailrows[0]['body']
        check('one_intercepted_mail_no_external_send',len(mailrows)==1)
        check('accepted_letter_verbatim',letter.decode() in body)
        check('no_stale_number_order_guidance','в том порядке, в котором их применяют' not in body)
        check('all_eight_filename_references',all(n in body for n in EXPECTED_NAMES))
        check('link_matches_existing_route','/download.php?o='+issued['id'] in body and '&f=p11' in body)
        snap=(delivery/EDITION['zip']).read_bytes()
        check('stored_archive_exact_accepted_sha',snap==accepted)
        check('stored_letter_exact_accepted_sha',(delivery/EDITION['letter']).read_bytes()==letter)
        with zipfile.ZipFile(io.BytesIO(snap)) as z:
            check('eight_members_crc_and_letter_outside',z.namelist()==EXPECTED_NAMES and z.testzip() is None and '00-PISMO-POSLE-POKUPKI.txt' not in z.namelist())
        r=call(issued,'notify')
        check('repeat_callback_preserves_order',r['order']==issued)
        check('repeat_callback_does_not_send_again',len(mailpath.read_text().splitlines())==1)
        code,raw,saved=get(issued)
        check('download_handler_200_exact_bytes',code==200 and raw==accepted)
        check('download_count_increment_once',saved['delivery']['downloads']==1)
        downloads['new_p11']={'code':code,'sha256':sha(raw),'bytes':len(raw)}
        messages['new_p11']={'sha256':sha(body.encode()),'letter_sha256':LETTER_SHA,'transport':'intercepted PHP mail; no external send'}
        # Denied requests do not consume a download.
        for label,mutator,override,expected in [
            ('unpaid_download',lambda o:o.update(status='pending'),None,403),
            ('wrong_token',lambda o:None,{'t':'wrong'},403),
            ('unowned_sku',lambda o:None,{'f':'p2'},404),
            ('expired',lambda o:o['delivery'].update(expires_at='2000-01-01T00:00:00Z'),None,410),
            ('quota',lambda o:o['delivery'].update(downloads=30),None,429),
            ('missing_edition_metadata',lambda o:o['delivery'].update(editions={}),None,500)]:
            o=copy.deepcopy(issued);mutator(o);c,b,a=get(o,overrides=override)
            check(label+'_fail_closed_no_counter',c==expected and a['delivery']['downloads']==o['delivery']['downloads'])
        # New issuance must not continue with a missing or changed input.
        for filename,original in [('accepted.zip',accepted),('accepted-letter.txt',letter)]:
            path=src/filename
            for mode in ['missing','changed']:
                if mode=='missing':path.unlink()
                else:path.write_bytes(original+b'!')
                fresh=new();q=call(fresh)
                check('source_'+filename+'_'+mode+'_no_partial_delivery',not q['result']['links'] and bool(q['result']['missing']) and q['order']==fresh)
                # Issued snapshots do not depend on current master availability.
                q=call(issued,'notify')
                check('issued_survives_'+filename+'_'+mode,q['order']==issued and q['result']==n['result'])
                path.write_bytes(original)
        for filename,original in [(EDITION['zip'],accepted),(EDITION['letter'],letter)]:
            path=delivery/filename
            for mode in ['missing','changed']:
                if mode=='missing':path.unlink()
                else:path.write_bytes(original+b'!')
                q=call(issued,'notify')
                check('issued_'+filename[:12]+'_'+mode+'_no_fallback',q['result']==[] and q['order']==issued and (not path.exists() if mode=='missing' else path.read_bytes()==original+b'!'))
                if filename==EDITION['zip']:
                    c,b,a=get(issued)
                    check('download_'+mode+'_snapshot_fails_without_count',c==500 and a['delivery']['downloads']==0)
                path.write_bytes(original)
        q=call(new(),extra={'P11_ENABLED':'0'})
        check('feature_disabled_no_new_issue',not q['result']['links'] and bool(q['result']['missing']))
        for label,mutate in [('unknown_edition',lambda o:o['items'][0]['edition'].update(kind='unknown')),
              ('wrong_hash',lambda o:o['items'][0]['edition'].update(sha256='0'*64)),
              ('unpaid_prepare',lambda o:o.update(status='pending')),
              ('standalone_t6_not_allowed',lambda o:o['items'][0].update(sku='t6')),
              ('mixed_order_missing_item',lambda o:o['items'].append({'sku':'nonexistent'}))]:
            o=new();mutate(o);q=call(o)
            check(label,not q['result']['links'] and bool(q['result']['missing']) and q['order']==o)
        # Synthetic historical snapshots have distinct bytes; no real customer data.
        for sku,dirname,zipname in [('p11','13-raschet-metrami','13-raschet-metrami.zip'),
                                  ('t6','19-kvartiry-vmesto-deneg','19-kvartiry-vmesto-deneg.zip')]:
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w') as z:z.writestr('old-'+sku+'.txt','historical '+sku+' bytes')
            historical=buf.getvalue();(delivery/zipname).write_bytes(historical)
            master=masters/dirname;master.mkdir();(master/'different-new-master.txt').write_text('MUST NOT REPLACE OLD ORDER')
            os.utime(master/'different-new-master.txt',(2100000000,2100000000))
            old=new(sku,False); old['id']='order_20261014_2_'+sku
            old['delivery']={'token':'legacytoken'+sku,'created_at':'2026-01-01T00:00:00Z',
                'expires_at':'2099-01-01T00:00:00Z','downloads':2,'items':{sku:zipname},'editions':[],
                'email_sent_at':'2026-01-01T00:00:00Z'}
            oldbytes=(delivery/zipname).read_bytes(); q=call(old,'notify')
            check('legacy_'+sku+'_callback_keeps_snapshot_token_order',q['order']==old and (delivery/zipname).read_bytes()==oldbytes)
            c,b,a=get(old,sku)
            check('legacy_'+sku+'_download_200_original',c==200 and b==historical and a['delivery']['token']==old['delivery']['token'])
            downloads['legacy_'+sku]={'code':c,'sha256':sha(b),'fixture':'synthetic historical snapshot'}
            injected=copy.deepcopy(old);injected['items'][0]['edition']=copy.deepcopy(EDITION)
            q=call(injected,'notify');c,b,a=get(q['order'],sku)
            check('legacy_'+sku+'_not_migrated_by_later_marker',q['order']==injected and c==200 and b==historical)
            before=(delivery/zipname).read_bytes();(delivery/zipname).unlink();q=call(old,'notify');c,b,a=get(old,sku)
            check('legacy_'+sku+'_missing_not_rebuilt_from_new_master',q['result']==[] and not (delivery/zipname).exists() and c==500 and a['delivery']['downloads']==2)
            (delivery/zipname).write_bytes(before)
        # An unmarked new P11 order retains the pre-existing generic route.
        u=new('p11',False);u['id']='order_20261014_3_unmarked';q=call(u)
        check('unmarked_order_not_upgraded','p11' not in q['order']['delivery']['editions'] and q['order']['delivery']['items']['p11']=='13-raschet-metrami.zip')
        # P1 pinned-edition code is left in place; verify one synthetic existing order.
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr('legacy-p1.txt','P1 existing edition')
        pb=buf.getvalue();ps=sha(pb);pn='p1-'+ps+'.zip';(delivery/pn).write_bytes(pb)
        p1=new('p1',False);p1['items'][0]['edition']={'zip':pn,'sha256':ps}
        q=call(p1);c,b,a=get(q['order'],'p1')
        check('p1_existing_edition_regression',c==200 and b==pb and q['order']['delivery']['editions']['p1']==p1['items'][0]['edition'])
        check('input_sources_unchanged',inputs=={n:read(n) for n in inputs} and accepted==read(ARCHIVE) and letter==read(LETTER))
        check('no_extra_mail_on_failed_or_legacy_calls',len(mailpath.read_text().splitlines())==1)
        version=subprocess.check_output(['php','-r','echo PHP_VERSION;'],timeout=5).decode()
    check('temporary_sandbox_removed',not Path(td).exists())
    return {'status':'PASS_AUTHOR_ISOLATED_BINDING_ONLY','source_commit':BASE,'checks':tests,
       'checks_passed':len(tests),'checks_total':len(tests),'downloads':downloads,'messages':messages,
       'archive_sha256':ARCHIVE_SHA,'letter_sha256':LETTER_SHA,'php_version':version,
       'modified_runtime_copy_sha256':{k:sha(v) for k,v in outputs.items()},'patch_sha256':sha(patch.encode()),
       'real_mail_sent':0,'real_payments':0,'live_orders_touched':0,'working_trees_modified':0,
       'native_office_jobs':0,'model_calls':0,'independent_acceptance':'PENDING','release':'HOLD',
       'G1_G8_accepted_products':0,'test_transport':'CLI full download.php handler; no HTTP listener or real checkout'},patch
