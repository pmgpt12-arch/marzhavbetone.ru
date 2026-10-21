#!/usr/bin/env python3
"""Remote preflight, exact rsync dry-run and private rollback rehearsal.
Never uploads site/config/order files and never changes a live webroot.
Reuses the existing SSH credentials, contract, manifest and concurrency lock.
"""
from __future__ import annotations
import base64, hashlib, json, os, shlex, subprocess, tempfile
from pathlib import Path
import inspect_backup as inspection

ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent
OUT=D/'evidence'


def run(args,timeout=90,**kwargs):
    p=subprocess.run(args,cwd=ROOT,timeout=timeout,capture_output=True,**kwargs)
    if p.returncode:
        # Commands in this phase contain no payment secrets or buyer records.
        err=p.stderr if isinstance(p.stderr,str) else p.stderr.decode('utf-8','replace')
        raise RuntimeError('DRY_RUN_COMMAND_FAILED exit='+str(p.returncode)+' '+err[-700:])
    return p


def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def ssh_args():
    key=Path(os.environ['MIGRATION_SSH_DIR'])
    return ['ssh','-i',str(key/'deploy_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
        '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(key/'known_hosts'),
        '-o','ConnectTimeout=15','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3',
        '-p',os.environ['SSH_PORT']]


PHP=r'''<?php
declare(strict_types=1);
ini_set('display_errors','0');set_time_limit(180);umask(0077);
function check(bool $ok,string $code):void {if(!$ok)throw new RuntimeException($code);}
function within(string $p,string $root):bool{return $p===$root||str_starts_with($p,$root.'/');}
function tree(string $root):array{
    $out=[];
    $it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS));
    foreach($it as $f){
        check(!$f->isLink(),'TREE_SYMLINK');
        if(!$f->isFile())continue;
        $name=substr($f->getPathname(),strlen($root)+1);
        $out[$name]=['size'=>$f->getSize(),'sha256'=>hash_file('sha256',$f->getPathname())];
    }
    ksort($out,SORT_STRING);return $out;
}
try{
    $p=json_decode(base64_decode('__PAYLOAD__',true),true,512,JSON_THROW_ON_ERROR);
    $paths=$p['paths'];$home=realpath((string)getenv('HOME'));
    check($home===$paths['home'],'AUTHORIZED_HOME_CHANGED');
    $old=realpath($paths['old_site']);$new=realpath($paths['new_site']);
    check($old===$paths['old_site']&&$new===$paths['new_site']&&$old!==$new,'WEBROOT_PATH_CHANGED');
    check(!is_link($old)&&!is_link($new)&&within($old,$home)&&within($new,$home),'WEBROOT_SYMLINK_OR_ESCAPE');
    check(is_writable($new)&&!file_exists($new.'/config.php'),'NEW_ROOT_NOT_EMPTY_CONFIG_GATE');
    $backupRoot=realpath($p['backup_location']);
    check(is_string($backupRoot)&&within($backupRoot,$home.'/nsp-migration-backups'),'BACKUP_PATH_OUTSIDE_PRIVATE_ROOT');
    $backups=[];
    foreach($p['backups'] as $name=>$b){
        $f=realpath($b['file']);
        check(is_string($f)&&within($f,$backupRoot)&&!is_link($f),'BACKUP_PATH_INVALID');
        check(filesize($f)===$b['size']&&hash_equals($b['sha256'],hash_file('sha256',$f)),'BACKUP_HASH_DRIFT');
        check((fileperms($f)&0077)===0,'BACKUP_PERMISSION_EXPOSED');
        exec('tar -tf '.escapeshellarg($f).' >/dev/null 2>&1',$unused,$rc);
        check($rc===0,'BACKUP_TAR_UNREADABLE');
        $backups[$name]=['sha256'=>$b['sha256'],'bytes'=>$b['size'],'verified'=>true];
    }
    $deltas=[];$bytes=0;
    foreach($p['shipping'] as $r){
        $rel=$r['file'];
        check($rel!==''&&!str_starts_with($rel,'/')&&!str_contains($rel,'..')&&!str_contains($rel,"\0"),'INVALID_SHIPPING_PATH');
        check(!preg_match('~^(config\.php|orders/|products-storage/|delivery/)~',$rel),'FORBIDDEN_SHIPPING_PATH');
        $cursor=$new;
        foreach(explode('/',$rel) as $part){$cursor.='/'.$part;check(!is_link($cursor),'SHIPPING_PARENT_SYMLINK');}
        $dest=$new.'/'.$rel;
        check(!is_dir($dest),'FILE_TARGET_IS_DIRECTORY');
        $actual=is_file($dest)?hash_file('sha256',$dest):null;
        $status=$actual===null?'CREATE':($actual===$r['sha256']?'UNCHANGED':'REPLACE');
        $deltas[]=['file'=>$rel,'action'=>$status,'old_sha256'=>$actual,'new_sha256'=>$r['sha256']];
        $bytes+=$r['size'];
    }
    check(disk_free_space($home)>$bytes*3+2*$p['backups']['new-site-before']['size']+33554432,'INSUFFICIENT_STAGING_SPACE');
    // Exercise recovery into a private sibling, never into either live root.
    $parent=$home.'/nsp-migration-private';
    check(!is_link($parent),'PRIVATE_PARENT_SYMLINK');
    if(!is_dir($parent))check(mkdir($parent,0700),'PRIVATE_PARENT_CREATE');
    chmod($parent,0700);
    $tag=$p['run'];check((bool)preg_match('/^run-[0-9]+$/D',$tag),'RUN_TAG_INVALID');
    $drill=$parent.'/'.$tag.'-rollback-drill';check(!file_exists($drill),'DRILL_ALREADY_EXISTS');
    check(mkdir($drill,0700),'DRILL_CREATE');
    $archive=$p['backups']['new-site-before']['file'];
    exec('tar -tf '.escapeshellarg($archive).' 2>/dev/null',$members,$rc);check($rc===0,'DRILL_LIST_FAILED');
    foreach($members as $member)check(!str_starts_with($member,'/')&&!in_array('..',explode('/',$member),true),'UNSAFE_ARCHIVE_MEMBER');
    exec('tar --no-same-owner --no-same-permissions -xf '.escapeshellarg($archive).' -C '.escapeshellarg($drill).' 2>/dev/null',$unused,$rc);
    check($rc===0,'DRILL_EXTRACT_FAILED');
    $restored=tree($drill);$current=tree($new);
    check($restored===$current,'NEW_ROOT_CHANGED_SINCE_BACKUP');
    // Record only code/path/hash metadata; no restored file contents leave host.
    $out=['status'=>'PASS_HOST_PLAN_AND_PRIVATE_ROLLBACK_REHEARSAL','run'=>$tag,
      'backups'=>$backups,'new_root_file_count'=>count($current),
      'new_root_tree_sha256'=>hash('sha256',json_encode($current,JSON_UNESCAPED_SLASHES)),
      'rollback_rehearsal'=>['location'=>$drill,'files'=>count($restored),'matches_current_new_root'=>true,
        'old_order_store_restored'=>false,'live_directory_modified'=>false],
      'shipping'=>$deltas,'shipping_bytes'=>$bytes,'live_webroots_modified'=>false];
    echo json_encode($out,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);
}catch(Throwable $e){
    $m=$e instanceof RuntimeException?$e->getMessage():'PRIVATE_PREFLIGHT_RUNTIME_ERROR';
    if(!preg_match('/^[A-Z0-9_]+$/D',$m))$m='SANITIZED_PREFLIGHT_ERROR';
    fwrite(STDERR,$m."\n");exit(2);
}
'''


def main():
    c=json.loads((D/'contract.json').read_text())
    route=json.loads((OUT/'route-review-checkpoint.json').read_text())
    plan=json.loads((OUT/'prepared-site-plan.json').read_text())
    previous=json.loads((OUT/'live-before-inspection.json').read_text())
    backups=json.loads((OUT/'private-backup-receipt.json').read_text())
    assert route['status']=='PASS_ROUTES_AND_CURRENT_13SKU_BROWSER'
    assert route['inherited_offer_defects_closed']==5 and route['retired_purchase_buttons']==0
    base=c['approved_base_commit'];run(['git','fetch','--no-tags','--depth=1','origin','main'],45,text=True)
    assert run(['git','rev-parse','FETCH_HEAD'],text=True).stdout.strip()==base,'MAIN_ADVANCED'
    assert inspection.repo_manifest()==json.loads((OUT/'repository-full-13sku-manifest.json').read_text())['products'],'SOURCE_PRODUCTS_DRIFT'
    files=[]
    for item in plan['shipping_files']:
        rel=item['file'];p=ROOT/rel
        assert not p.is_symlink() and p.is_file() and p.resolve().is_relative_to(ROOT)
        assert rel!='config.php' and not rel.startswith(('orders/','products-storage/','delivery/','tools/'))
        assert p.stat().st_size==item['size'] and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],'CANDIDATE_SHA_DRIFT:'+rel
        files.append(rel)
    assert len(files)==len(set(files)) and len([p for p in files if p.endswith('.html')])==88
    before=inspection.remote('inspect')
    assert before['products']==previous['products'],'LIVE_172_FILE_MANIFEST_DRIFT'
    for key in ['paths','code_sha256','config_sha256_not_contents']:
        assert before[key]==previous[key],'LIVE_BASELINE_CHANGED:'+key
    assert not before['runtime']['new_config_exists'] and before['runtime']['ttl_seconds']==3600
    write('dry-run-live-inspection.json',before)
    payload={'paths':before['paths'],'backup_location':backups['backup_location'],
      'backups':backups['backups'],'shipping':plan['shipping_files'],'run':'run-'+os.environ['GITHUB_RUN_ID']}
    encoded=base64.b64encode(json.dumps(payload).encode()).decode()
    assert PHP.count('__PAYLOAD__')==1
    host=os.environ['USER']+'@'+os.environ['HOST']
    result=run([*ssh_args(),host,'php -f /dev/stdin'],240,input=PHP.replace('__PAYLOAD__',encoded),text=True)
    host_plan=json.loads(result.stdout);write('new-root-host-plan.json',host_plan)
    with tempfile.TemporaryDirectory(prefix='nsp-rsync-dry-') as td:
        selection=Path(td)/'files.txt';selection.write_text('\n'.join(sorted(files))+'\n')
        args=['rsync','--dry-run','--recursive','--checksum','--itemize-changes','--protect-args',
          '--no-implied-dirs','--out-format=%i\t%n','--files-from='+str(selection),
          '-e',shlex.join(ssh_args()),str(ROOT)+'/',host+':'+before['paths']['new_site']+'/']
        assert '--dry-run' in args and not any(x.startswith('--delete') for x in args)
        transferred=run(args,180,text=True).stdout
    deltas=[]
    for line in transferred.splitlines():
        if not line.strip():continue
        assert '\t' in line,('UNEXPECTED_RSYNC_OUTPUT',line[:100])
        mode,path=line.split('\t',1);path=path.removeprefix('./')
        assert not mode.startswith('*deleting'),'DELETE_IN_DRY_RUN'
        if len(mode)>1 and mode[1]=='f':
            assert path in files,'RSYNC_SCOPE_ESCAPE:'+path
            deltas.append({'path':path,'change':mode})
        else:
            assert path.endswith('/') and any(x.startswith(path) for x in files),'RSYNC_UNEXPECTED_ENTRY:'+path
    expected={x['file'] for x in host_plan['shipping'] if x['action']!='UNCHANGED'}
    assert {x['path'] for x in deltas}==expected,'RSYNC_AND_INDEPENDENT_HASH_PLAN_DISAGREE'
    after=inspection.remote('inspect')
    for key in ['paths','products','code_sha256','config_sha256_not_contents','new_root_index_sha256']:
        assert after[key]==before[key],'LIVE_STATE_MODIFIED_DURING_DRY_RUN:'+key
    report={'status':'PASS_EXACT_REMOTE_DRY_RUN_AND_ROLLBACK','run':os.environ['GITHUB_RUN_ID'],
      'candidate_commit':run(['git','rev-parse','HEAD'],text=True).stdout.strip(),'source_main':base,
      'shipping_files':len(files),'html_pages':88,'buyer_files':172,'active_skus':13,
      'rsync_file_changes':deltas,'independent_plan_matches':True,
      'backup_archive_hashes_verified':len(host_plan['backups']),
      'private_rollback_rehearsal':host_plan['rollback_rehearsal'],
      'config_in_upload':False,'masters_or_orders_in_upload':False,'deletions':0,
      'old_site_config_and_handlers_unchanged':True,'both_public_roots_unchanged':True,
      'production_cutover':False,'payment_submitted':False,
      'next':'private isolated candidate with live masters read-only, fresh sandbox orders and disabled payment; then controlled new-root acceptance'}
    write('remote-dry-run.json',report)
    print('PASS_REMOTE_DRY_RUN',len(files),'SHIPPING_FILES',len(deltas),'CHANGES',
      '13_SKUS_172_FILES_UNCHANGED FOUR_BACKUPS_VERIFIED PRIVATE_ROLLBACK_REHEARSED NO_PUBLIC_WRITES',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        write('remote-dry-run-failure.json',{'status':'FAIL','run':os.getenv('GITHUB_RUN_ID'),
          'error':type(exc).__name__+':'+str(exc)[:2000],'live_upload_attempted':False})
        raise
