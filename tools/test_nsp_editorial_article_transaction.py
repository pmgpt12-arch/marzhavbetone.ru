from pathlib import Path
from hashlib import sha256
import json, subprocess, os, tempfile, sys
SCRIPT=Path(__file__).with_name('nsp_editorial_article_transaction.php')

def sha(data):return sha256(data).hexdigest()
def call(mode,root,stage,approval=None):
    env=os.environ.copy();env.pop('NSP_EDITORIAL_APPROVED_MANIFEST_SHA256',None)
    if approval:env['NSP_EDITORIAL_APPROVED_MANIFEST_SHA256']=approval
    return subprocess.run(['php',str(SCRIPT),mode,str(root),str(stage)],text=True,capture_output=True,env=env,timeout=20)

def setup(base):
    root=base/'nastoronepodryadchika.ru'; root.mkdir(); (root/'articles').mkdir()
    stage=base/'private';stage.mkdir();(stage/'candidate'/'articles').mkdir(parents=True)
    (root/'checkout.php').write_text('<?php // checkout baseline')
    (root/'products-config.php').write_text('<?php // products baseline')
    rows=[];protected=[]
    for i in range(43):
        path=f'articles/a{i:02d}.html'
        prior=f'<!doctype html><h1>Old article {i}</h1>'.encode()
        new=f'<!doctype html><h1>New article {i}</h1><p>3 previews</p>'.encode()
        (root/path).write_bytes(prior)
        if i<32:
            (stage/'candidate'/path).write_bytes(new)
            rows.append({'path':path,'before_sha256':sha(prior),'after_sha256':sha(new),'bytes':len(new)})
        else:protected.append({'path':path,'sha256':sha(prior)})
    cssold=b'.article-page{max-width:800px}'
    cssnew=b'.article-page{max-width:800px}.nsp-document-preview img{max-width:100%}'
    (root/'article.css').write_bytes(cssold)
    (stage/'candidate'/'article.css').write_bytes(cssnew)
    m={'schema':'NSP_ARTICLE_ONLY_RELEASE_MANIFEST_v1','target_host':'nastoronepodryadchika.ru','release_status':'PREFLIGHT_ONLY_NO_PRODUCTION_WRITE','changed_files':rows,'protected_approved_articles':protected,'image_uploads':0,'style_asset':{'path':'article.css','before_sha256':sha(cssold),'after_sha256':sha(cssnew),'bytes':len(cssnew)}}
    mb=(json.dumps(m,ensure_ascii=False,indent=2)+'\n').encode()
    (stage/'manifest.json').write_bytes(mb)
    return root,stage,sha(mb),m

def check(tag,condition,tests):
    if not condition:raise AssertionError(tag)
    tests.append(tag)

def main():
    tests=[]
    with tempfile.TemporaryDirectory(prefix='nsp-article-fixture-') as t:
        root,stage,approval,m=setup(Path(t))
        r=call('dry-run',root,stage)
        check('dry-run 33 files PASS and no writes',r.returncode==0 and json.loads(r.stdout)['production_writes']==0,tests)
        check('before unchanged',sha((root/'articles/a00.html').read_bytes())==m['changed_files'][0]['before_sha256'],tests)
        r=call('apply',root,stage)
        check('apply without owner approval FAIL',r.returncode!=0 and 'OWNER_LEGAL_RELEASE_APPROVAL_REQUIRED' in r.stderr,tests)
        check('no backup or public writes on rejected approval',not (stage/'original').exists() and sha((root/'articles/a00.html').read_bytes())==m['changed_files'][0]['before_sha256'],tests)
        (root/'articles/a00.html').write_text('CONCURRENT CHANGE')
        r=call('dry-run',root,stage)
        check('fail-closed live SHA drift',r.returncode!=0 and 'LIVE_BEFORE_DRIFT' in r.stderr,tests)
        (root/'articles/a00.html').write_bytes(b'<!doctype html><h1>Old article 0</h1>')
        (root/'articles/a34.html').write_text('PROTECTED MODIFIED')
        r=call('dry-run',root,stage)
        check('fail-closed approved article SHA drift',r.returncode!=0 and 'APPROVED_ARTICLE_CHANGED' in r.stderr,tests)
        (root/'articles/a34.html').write_text('<!doctype html><h1>Old article 34</h1>')
        r=call('apply',root,stage,approval='0'*64)
        check('wrong approval hash FAIL',r.returncode!=0 and 'OWNER_LEGAL_RELEASE_APPROVAL_REQUIRED' in r.stderr,tests)
        r=call('apply',root,stage,approval=approval)
        check('correct scoped apply PASS',r.returncode==0 and json.loads(r.stdout)['files']==33,tests)
        check('candidate and css exactly match expected',all(sha((root/x['path']).read_bytes())==x['after_sha256'] for x in m['changed_files']+[m['style_asset']]),tests)
        r=call('verify',root,stage)
        check('post-apply verify PASS',r.returncode==0 and json.loads(r.stdout)['protected_runtime']=='UNCHANGED',tests)
        r=call('rollback',root,stage)
        check('rollback PASS',r.returncode==0,tests)
        check('restores all 33 original SHA',all(sha((root/x['path']).read_bytes())==x['before_sha256'] for x in m['changed_files']+[m['style_asset']]),tests)
        check('11 protected untouched',all(sha((root/x['path']).read_bytes())==x['sha256'] for x in m['protected_approved_articles']),tests)
        check('protected PHP untouched',(root/'checkout.php').read_text()=='<?php // checkout baseline',tests)
        (root/'articles/a00.html').write_text('tamper after rollback')
        r=call('rollback',root,stage)
        check('rollback refuses concurrent tampering',r.returncode!=0 and 'ROLLBACK_CONCURRENT_EDIT' in r.stderr,tests)
    print(json.dumps({'status':'PASS','tests':len(tests),'cases':tests,'production_writes':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
