#!/usr/bin/env python3
"""Stage accepted shipping allowlist privately and test actual 13 master ZIPs.
Requires the successful exact remote dry-run. No public directory switch.
"""
from __future__ import annotations
import base64,hashlib,json,os,shlex,tempfile
from pathlib import Path
import inspect_backup as inspection
from dry_run_new import run,ssh_args

ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent
OUT=D/'evidence'


def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    c=json.loads((D/'contract.json').read_text())
    dry=json.loads((OUT/'remote-dry-run.json').read_text())
    host_plan=json.loads((OUT/'new-root-host-plan.json').read_text())
    plan=json.loads((OUT/'prepared-site-plan.json').read_text())
    old=json.loads((OUT/'dry-run-live-inspection.json').read_text())
    accepted=json.loads((OUT/'repository-full-13sku-manifest.json').read_text())['products']
    assert dry['status']=='PASS_EXACT_REMOTE_DRY_RUN_AND_ROLLBACK' and dry['backup_archive_hashes_verified']==4
    assert dry['private_rollback_rehearsal']['matches_current_new_root']
    run(['git','fetch','--no-tags','--depth=1','origin','main'],45,text=True)
    assert run(['git','rev-parse','FETCH_HEAD'],text=True).stdout.strip()==c['approved_base_commit'],'MAIN_ADVANCED'
    assert inspection.repo_manifest()==accepted,'SOURCE_BUYER_MANIFEST_DRIFT'
    files=[]
    for item in plan['shipping_files']:
        path=ROOT/item['file']
        assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT)
        assert item['file']!='config.php' and not item['file'].startswith(('products-storage/','orders/','tools/','delivery/'))
        assert path.stat().st_size==item['size'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'],'SHIP_HASH_DRIFT'
        files.append(item['file'])
    assert len(files)==dry['shipping_files']==len(set(files))
    before=inspection.remote('inspect')
    for key in ['paths','products','code_sha256','config_sha256_not_contents','new_root_index_sha256']:
        assert before[key]==old[key],'LIVE_CHANGED_SINCE_DRY_RUN:'+key
    assert not before['runtime']['new_config_exists']
    candidate=run(['git','rev-parse','HEAD'],text=True).stdout.strip()
    payload={'paths':before['paths'],'products':accepted,'shipping':plan['shipping_files'],
      'run':'run-'+os.environ['GITHUB_RUN_ID'],'candidate_commit':candidate,
      'new_root_tree_sha256':host_plan['new_root_tree_sha256'],
      'site_url':'https://'+c['new_domain'],'support_email':c['support_email_preserve_until_verified']}
    script=(D/'stage_private.php').read_text();assert script.count('__PAYLOAD__')==1
    script=script.replace('__PAYLOAD__',base64.b64encode(json.dumps(payload).encode()).decode())
    host=os.environ['USER']+'@'+os.environ['HOST']
    def remote(phase):
        assert phase in {'init','verify-build'}
        response=run([*ssh_args(),host,'php -f /dev/stdin -- '+phase],240,input=script,text=True)
        return json.loads(response.stdout)
    created=remote('init');write('private-stage-created.json',created)
    expected=before['paths']['home']+'/nsp-migration-private/'+payload['run']+'-stage/site'
    assert created['site']==expected and created['status']=='PASS_PRIVATE_STAGE_CREATED'
    with tempfile.TemporaryDirectory(prefix='nsp-private-stage-files-') as td:
        selection=Path(td)/'files.txt';selection.write_text('\n'.join(sorted(files))+'\n')
        command=['rsync','--recursive','--checksum','--protect-args','--no-implied-dirs',
          '--files-from='+str(selection),'-e',shlex.join(ssh_args()),str(ROOT)+'/',host+':'+created['site']+'/']
        assert not any(x.startswith('--delete') for x in command)
        assert '/nsp-migration-private/' in command[-1] and not command[-1].endswith('/www/'+c['new_domain']+'/')
        run(command,180,text=True)
    verified=remote('verify-build')
    assert verified['status']=='PASS_PRIVATE_HOST_CANDIDATE_AND_13_ARCHIVES'
    assert verified['active_skus']==13 and verified['buyer_files']==172 and verified['emails_sent']==0
    assert set(verified['products'])==set(accepted)
    for sku,result in verified['products'].items():
        assert result['files']==len(accepted[sku]['files']) and result['crc_pass'] and result['member_sha256_pass']
        assert result['ttl_seconds']==3600 and result['token_reuse_pass'] and result['download_host']==c['new_domain']
    after=inspection.remote('inspect')
    for key in ['paths','products','code_sha256','config_sha256_not_contents','new_root_index_sha256']:
        assert after[key]==before[key],'LIVE_MODIFIED_DURING_PRIVATE_STAGING:'+key
    verified.update(run=os.environ['GITHUB_RUN_ID'],source_main=c['approved_base_commit'],
      old_live_handlers_config_and_masters_unchanged=True,
      live_order_counts_before=before['orders_counts_only'],live_order_counts_after=after['orders_counts_only'],
      public_http_downloads_verified=False,production_cutover=False)
    write('private-stage-verification.json',verified)
    print('PASS_PRIVATE_HOST_STAGE',len(files),'SITE_FILES 13_ZIPS 172_MEMBER_SHA_AND_CRC',
      'ONE_HOUR_TOKENS_NO_SEND_NO_REAL_PAYMENT_NO_PUBLIC_CHANGE',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        write('private-stage-failure.json',{'status':'FAIL','run':os.getenv('GITHUB_RUN_ID'),
          'error':type(exc).__name__+':'+str(exc)[:2000],'public_root_switch_attempted':False})
        raise
