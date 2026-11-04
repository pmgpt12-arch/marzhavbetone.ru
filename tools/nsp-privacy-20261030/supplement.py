"""Inspect only unidentified backup order records and legacy log metadata; no contacts emitted."""
import collections,json,re,sys
from pathlib import Path
h=Path(sys.argv[1]);old={p.name for p in (h/'www/marzhavbetone.ru/orders').glob('order_*.json')};groups={}
for p in (h/'nsp-migration-private').rglob('order_*.json'):
 if p.is_symlink() or p.name in old:continue
 r=json.loads(p.read_bytes());area=p.relative_to(h/'nsp-migration-private').parts[0];g=groups.setdefault(area,{'records':0,'statuses':{},'email_records':0,'phone_records':0,'created_before_cutover':0,'created_after_cutover':0,'missing_created':0,'non_100_paid_records':0,'paid_records':0,'synthetic_email_records':0,'schema_keysets':[]});g['records']+=1
 status=str(r.get('status','[missing]'));status=status if status in ('paid','pending','canceled','cancelled','succeeded','failed') else '[other]';g['statuses'][status]=g['statuses'].get(status,0)+1
 g['email_records']+=bool(r.get('email'));g['phone_records']+=bool(r.get('phone'));created=str(r.get('created_at',''));g['created_before_cutover']+=bool(created) and created[:10]<'2026-10-20';g['created_after_cutover']+=bool(created) and created[:10]>='2026-10-20';g['missing_created']+=not bool(created);paid=status in ('paid','succeeded') or bool(r.get('paid_at'));g['paid_records']+=paid;g['non_100_paid_records']+=paid and r.get('total')!=100
 email=str(r.get('email',''));g['synthetic_email_records']+=email.lower().split('@')[-1] in ('example.com','example.invalid','example.test','test.invalid','localhost')
 keys=sorted(k for k in r if re.fullmatch(r'[a-z_]{1,40}',k));
 if keys not in g['schema_keysets']:g['schema_keysets'].append(keys)
logs=[]
for p in (h/'logs').rglob('*'):
 if p.is_file() and 'marzhavbetone.ru' in p.name:logs.append({'name':p.name,'bytes':p.stat().st_size,'writable':p.stat().st_uid==__import__('os').getuid(),'symlink':p.is_symlink()})
print(json.dumps({'status':'READ_ONLY','unknown_backup_groups':groups,'legacy_log_metadata':logs},indent=2))
