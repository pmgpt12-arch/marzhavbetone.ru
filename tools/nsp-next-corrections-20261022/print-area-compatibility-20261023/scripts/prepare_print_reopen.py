from pathlib import Path
import hashlib,base64,json
Q=Path('/home/denis/projects/nsp-audit-fixes-20261021/qa/next-corrections-20261022');p=Q/'print-area-name-matrix-20261023/evidence/pd2-filled.xlsx';data=p.read_bytes();x=[{'name':'native-saved.xlsx','sheet':'PrintTest','sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()}]
(Q/'print-diagnostic-reopen-transfer.json').write_text(json.dumps(x))
old=(Q/'scripts/run_print_diagnostic.py').read_text();new=old.replace("D=Q/'print-area-diagnostic-20261023'","D=Q/'print-area-reopen-20261023'").replace("jid='nsp-print-area-diagnostic-v1-20261023'","jid='nsp-print-area-reopen-v1-20261023'").replace("Q/'print-diagnostic-transfer.json'","Q/'print-diagnostic-reopen-transfer.json'")
new=new.replace('assert len(names)==2','assert len(names)==2').replace("and names[0].text==\"'\"+x['sheet']+\"'!$A$1:$A$3\"","and names[0].text==x['sheet']+\"!$A$1:$A$3\"")
new=new.replace('for i in [1,2]:','for i in [1]:');assert old!=new;compile(new,'reopen','exec')
(Q/'scripts/run_print_reopen.py').write_text(new);print('PREPARED_NATIVE_SAVED_REOPEN',x[0]['sha256'])
