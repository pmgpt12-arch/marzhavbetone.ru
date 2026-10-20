#!/usr/bin/env python3
"""Classify the observed 15 failures against the exact previous checkout."""
from pathlib import Path
import json,subprocess,tempfile,yaml
R=Path(__file__).resolve().parents[1];O=R/'tools/candidates/remaining-batch-r3-20261018/release-20261020'
ids=['check_artifact_registry','test_artifact_registry','check_packages','sync_kit_file_counts','test_sync_kit_file_counts','build_preview','test_official_forms','test_p1_price_http','test_p1_print_layout','test_no_refund_sales_disclaimer','test_p1_value_language','verify_delivery_zips','test_diagnostic_sku_standalone','test_normative_gate','normative_gate']
required={'check_artifact_registry','test_artifact_registry','test_official_forms','test_p1_price_http','test_p1_print_layout','test_p1_value_language','verify_delivery_zips','test_diagnostic_sku_standalone','test_normative_gate','normative_gate'}
rows=[];fail=[]
with tempfile.TemporaryDirectory(prefix='r3-gate-baseline-') as tmp:
 old=Path(tmp)/'baseline';subprocess.run(['git','worktree','add','--detach',str(old),'7ac3535'],cwd=R,check=True,timeout=30,capture_output=True)
 try:
  oldchecks={v['id']:v for v in yaml.safe_load((old/'tools/ci_checks.yaml').read_text())['проверки']};checks={v['id']:v for v in yaml.safe_load((R/'tools/ci_checks.yaml').read_text())['проверки']}
  for name in ids:
   result={'id':name}
   for label,root,commands in [('previous',old,oldchecks),('current',R,checks)]:
    p=subprocess.run(['bash','-c',commands[name]['команда']],cwd=root,capture_output=True,text=True,timeout=90)
    result[label]={'exit':p.returncode,'output':p.stdout+p.stderr}
   before,after=result['previous']['exit'],result['current']['exit']
   result['classification']='CURRENT_PASS' if after==0 else 'PREEXISTING_FAILURE_RETAINED' if before!=0 else 'NEW_FAILURE'
   if after and (before==0 or name in required):fail.append(name)
   print(name,result['classification'],flush=True);rows.append(result)
 finally:subprocess.run(['git','worktree','remove','--force',str(old)],cwd=R,check=True,timeout=30)
report={'status':'PASS_NO_NEW_FAILURES_REQUIRED_RELEASE_CONTRACTS_PASS' if not fail else 'FAIL_REQUIRED_OR_NEW_FAILURE','baseline_commit':'7ac3535fbfb539cebb6aedd8991ffa19937ff38c','current_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'historical_failures_not_relabelled_PASS':True,'blocking':fail,'checks':rows}
(O/'integration-check-classification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(report['status'],'blocking=',fail,flush=True)
raise SystemExit(bool(fail))
