#!/usr/bin/env python3
"""Regression: large SSH exec packets and PHP stdin argument displacement."""
from pathlib import Path
import base64,json,subprocess
source=(Path(__file__).resolve().parent/'release_remaining_only.py').read_text()
assert "cmd='php -f /dev/stdin -- '" in source
assert 'len(cmd.encode())<4096' in source and 'input=code' in source
payload=base64.b64encode(b'x'*100000).decode()
code='<?php echo json_encode(["args"=>$argv,"bytes"=>strlen(base64_decode("'+payload+'"))]);'
r=subprocess.run(['php','-f','/dev/stdin','--','www/site','products','preflight'],input=code,text=True,capture_output=True,check=True,timeout=10)
d=json.loads(r.stdout);assert d['args'][1:]==['www/site','products','preflight'] and len(d['args'])==4 and d['bytes']==100000,d
print('PASS PHP stdin preserves 4 argv entries and 100000-byte payload outside exec request')
