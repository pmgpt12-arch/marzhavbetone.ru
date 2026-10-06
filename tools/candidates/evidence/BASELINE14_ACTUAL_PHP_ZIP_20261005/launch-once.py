from pathlib import Path
import subprocess,json,os,datetime,hashlib
R=Path(__file__).resolve().parent
assert (R/'ROOT_AUTHORIZATION.json').is_file(), 'ROOT_AUTHORIZATION_REQUIRED'
assert not (R/'execution-receipt.json').exists(), 'NO_BLIND_RETRY'
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
launch={'native_parent_pid':os.getpid(),'start_utc':start,'command':['python3',str(R/'run.py')],'concurrency':'4 Python ThreadPoolExecutor workers; not4 separate OS PIDs','runner_sha256':hashlib.sha256((R/'run.py').read_bytes()).hexdigest(),'wrapper_sha256':hashlib.sha256((R/'build-one.php').read_bytes()).hexdigest()}
(R/'process-start.json').write_text(json.dumps(launch,indent=2)+'\n')
try:
 with (R/'execution.log').open('w') as log:
  child=subprocess.Popen(launch['command'],stdout=log,stderr=subprocess.STDOUT)
  launch['runner_pid']=child.pid;(R/'process-start.json').write_text(json.dumps(launch,indent=2)+'\n')
  try:code=child.wait(timeout=450)
  except subprocess.TimeoutExpired:
   child.terminate();code=child.wait(timeout=15)
 receipt={**launch,'exit_code':code,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'log_sha256':hashlib.sha256((R/'execution.log').read_bytes()).hexdigest(),'status':'COMPLETED_SUCCESS' if code==0 else 'FAILED_RETAINED_NO_RETRY'}
 (R/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt),flush=True)
except Exception as e:
 (R/'execution-receipt.json').write_text(json.dumps({**launch,'status':'LAUNCH_FAILURE_RETAINED','exception':str(e)},indent=2)+'\n');raise
