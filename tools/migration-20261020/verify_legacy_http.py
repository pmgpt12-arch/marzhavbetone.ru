#!/usr/bin/env python3
"""Read-only exact HTML gate for the existing Cloudflare-fronted old domain.
No server write, no credentials, no payment calls and no relaxed business content.
"""
from __future__ import annotations
import hashlib,json,os,subprocess
from pathlib import Path
from diagnose_http import request
from legacy_http_gate import self_test,verify

D=Path(__file__).resolve().parent
ROOT=D.parents[1]
OUT=D/'evidence'

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    contract=json.loads((D/'contract.json').read_text())
    base=contract['approved_base_commit']
    result={'gate':'EXACT_LEGACY_HTTP_WITH_OBSERVED_CLOUDFLARE_TRANSFORMS',
      'run':os.getenv('GITHUB_RUN_ID'),'status':'RUNNING',
      'production_touched':False,'payment_submitted':False,'checks':[]}
    try:
        fetched=subprocess.run(['git','rev-parse','FETCH_HEAD'],cwd=ROOT,text=True,capture_output=True)
        # The bounded workflow fetches main immediately before invoking this gate.
        assert fetched.returncode==0 and fetched.stdout.strip()==base,'MAIN_HEAD_CHANGED'
        source=subprocess.run(['git','show',base+':index.html'],cwd=ROOT,capture_output=True,check=True,timeout=20).stdout
        baseline=json.loads((OUT/'live-before-inspection.json').read_text())
        assert sha(source)==baseline['code_sha256']['index.html'],'OLD_ORIGIN_BASELINE_DRIFT'
        result['origin_sha256']=sha(source)
        result['negative_mutations']=self_test(source)
        for suffix in ('/','/','/index.html'):
            data,meta=request('https://'+contract['old_domain']+suffix)
            assert meta['status']==200,'OLD_DOMAIN_HTTP_NOT_200'
            assert meta['final_url'].startswith('https://'+contract['old_domain']+'/'),'OLD_DOMAIN_REDIRECTED'
            verified=verify(data,source)
            result['checks'].append({'path':suffix,'status':meta['status'],
                'raw_http_sha256':verified['raw_http_sha256'],
                'normalized_sha256':verified['normalized_sha256'],
                'transformations':verified['transformations']})
        assert len(result['checks'])==3
        result['status']='PASS_EXACT_LEGACY_HTTP_CONTENT_WITH_CDN_TRANSFORMS'
        print('EXACT_LEGACY_HTTP_PASS 3_RESPONSES 5_NEGATIVE_MUTATIONS_REJECTED',flush=True)
    except Exception as exc:
        result['status']='FAIL_LEGACY_HTTP_GATE'
        result['error']=type(exc).__name__+':'+str(exc)[:200]
        raise
    finally:
        (OUT/'legacy-http-acceptance.json').write_text(
          json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
