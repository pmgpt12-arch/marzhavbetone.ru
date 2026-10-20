#!/usr/bin/env python3
"""Read-only comparison of legacy origin HTML and actual public responses.
No SSH, payments, credentials, source mutations or public writes.
"""
from __future__ import annotations
import difflib,gzip,hashlib,json,os,subprocess,urllib.request
from pathlib import Path
D=Path(__file__).resolve().parent
ROOT=D.parents[1]
OUT=D/'evidence'


def digest(data):return hashlib.sha256(data).hexdigest()


def request(url):
    q=urllib.request.Request(url,headers={'User-Agent':'NSP-Migration-Acceptance/1.0','Cache-Control':'no-cache','Accept-Encoding':'identity'})
    with urllib.request.urlopen(q,timeout=15) as r:
        raw=r.read(1000000);assert len(raw)<1000000
        headers={k.lower():v for k,v in r.headers.items()}
        decoded=gzip.decompress(raw) if headers.get('content-encoding')=='gzip' else raw
        return decoded,{'status':r.status,'final_url':r.url,'bytes':len(decoded),'raw_sha256':digest(raw),'decoded_sha256':digest(decoded),
          'headers':{k:headers[k] for k in ['server','content-type','content-encoding','etag','cf-cache-status','cf-ray','cache-control'] if k in headers}}


def differences(a,b):
    # Public HTML only. Do not dump buyer records, cookies or private URLs.
    out=[]
    matcher=difflib.SequenceMatcher(None,a.splitlines(),b.splitlines(),autojunk=False)
    left=a.splitlines();right=b.splitlines()
    for action,i,j,k,l in matcher.get_opcodes():
        if action=='equal':continue
        out.append({'kind':action,'source_lines':[i+1,j],'response_lines':[k+1,l],
          'source_excerpt':'\n'.join(left[i:j])[:1400],'response_excerpt':'\n'.join(right[k:l])[:2600]})
    return out


def main():
    c=json.loads((D/'contract.json').read_text());base=c['approved_base_commit']
    subprocess.run(['git','fetch','--no-tags','--depth=1','origin','main'],cwd=ROOT,check=True,timeout=35,capture_output=True)
    head=subprocess.check_output(['git','rev-parse','FETCH_HEAD'],cwd=ROOT,text=True).strip()
    assert head==base,'MAIN_ADVANCED'
    source=subprocess.check_output(['git','show',base+':index.html'],cwd=ROOT,timeout=15)
    first,a=request('https://'+c['old_domain']+'/')
    second,b=request('https://'+c['old_domain']+'/')
    explicit,z=request('https://'+c['old_domain']+'/index.html')
    expected=json.loads((OUT/'live-before-inspection.json').read_text())['code_sha256']['index.html']
    assert digest(source)==expected,'SOURCE_NOT_ACTUAL_ORIGIN_BASELINE'
    report={'status':'READ_ONLY_HTTP_REPRESENTATION_DIAGNOSIS','run':os.getenv('GITHUB_RUN_ID'),
      'origin_source_sha256':expected,'origin_bytes':len(source),
      'first':a,'second':b,'explicit_index':z,'origin_equals_response':source==first,
      'consecutive_responses_identical':first==second,
      'origin_to_public_changes':differences(source.decode(),first.decode()),
      'public_to_public_changes':differences(first.decode(),second.decode()),
      'explicit_index_changes':differences(source.decode(),explicit.decode()),
      'previous_failure':'OLD_STOREFRONT_CHANGED compared HTTP bytes with filesystem bytes; classify after reading this evidence',
      'production_changed':False}
    (OUT/'legacy-http-diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('HTTP_DIAGNOSIS_COMPLETE',len(report['origin_to_public_changes']),'SOURCE_DIFFS',len(report['public_to_public_changes']),'RESPONSE_DIFFS',flush=True)


if __name__=='__main__':main()
