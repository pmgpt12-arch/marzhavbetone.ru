#!/usr/bin/env python3
"""Read-only provider webhook inventory. No payment, mail or production writes."""
from __future__ import annotations
import base64,json,os
from pathlib import Path
from dry_run_new import run,ssh_args
import inspect_backup as inspection

D=Path(__file__).resolve().parent
OUT=D/'evidence'
def main():
    baseline=json.loads((OUT/'dry-run-live-inspection.json').read_text())
    before=inspection.remote('inspect')
    for k in ['paths','products','code_sha256','config_sha256_not_contents']:
        assert before[k]==baseline[k],'OLD_STORE_CHANGED:'+k
    payload={'old_site':before['paths']['old_site'],
      'old_config_sha256':before['config_sha256_not_contents']}
    php=(D/'provider_webhook_audit.php').read_text()
    assert php.count('__PAYLOAD__')==1
    php=php.replace('__PAYLOAD__',base64.b64encode(json.dumps(payload).encode()).decode())
    host=os.environ['USER']+'@'+os.environ['HOST']
    result=run([*ssh_args(),host,'php -f /dev/stdin'],45,input=php,text=True)
    report=json.loads(result.stdout)
    assert report['mutation'] is False and report['payment_created'] is False
    after=inspection.remote('inspect')
    for k in ['paths','products','code_sha256','config_sha256_not_contents']:
        assert after[k]==before[k],'PROVIDER_AUDIT_CHANGED_LIVE_STORE:'+k
    report['old_store_unchanged']=True
    report['production_cutover']=False
    report['run']=os.environ.get('GITHUB_RUN_ID')
    (OUT/'provider-webhook-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('PROVIDER_AUDIT',report['status'],'HTTP',report['http_status'],
      'WEBHOOKS',report.get('webhook_count','UNKNOWN'),'NO_MUTATION',flush=True)
    if report['status']!='PASS_PROVIDER_WEBHOOK_INVENTORY':
        raise RuntimeError('PROVIDER_WEBHOOK_INVENTORY_NOT_AUTHORIZED')
if __name__=='__main__':main()
