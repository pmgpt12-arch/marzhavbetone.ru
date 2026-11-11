"""Privacy cleanup acceptance: no current-data loss, no raw-contact copy, exact-plan and real-payment guards."""
import importlib.util
import io
import json
import tarfile
import tempfile
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).with_name('cleanup.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

with tempfile.TemporaryDirectory() as temporary:
    home = Path(temporary)
    old = home / 'www/marzhavbetone.ru/orders'
    current = home / 'nsp-production-private/orders'
    old.mkdir(parents=True)
    current.mkdir(parents=True)
    current_payload = b'{"email":"current@example.invalid"}'
    (current / 'keep.json').write_bytes(current_payload)
    rows = [dict(id='order_20260701_aaa', status='canceled', created_at='2026-07-01', email='private@example.invalid'),
            dict(id='order_20260701_bbb', status='paid', total=100, email='paid@example.invalid', phone='private',
                 delivery={'token':'private'}, items=[{'sku':'p1','price':100,'customer':'private'}])]
    for row in rows:
        (old / (row['id'] + '.json')).write_text(json.dumps(row))
    backup = home / 'nsp-migration-backups'
    backup.mkdir()
    (backup / (rows[0]['id'] + '.json')).write_text(json.dumps(rows[0]))
    with zipfile.ZipFile(backup/'copy.zip', 'w') as archive:
        archive.writestr('orders/'+rows[0]['id']+'.json', json.dumps(rows[0]))
        archive.writestr('keep.txt', b'keep-zip-exact')
    with tarfile.open(backup/'copy.tar.gz', 'w:gz') as archive:
        for name, data in [('orders/'+rows[1]['id']+'.json', json.dumps(rows[1]).encode()), ('keep.txt', b'keep-tar-exact')]:
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    logs = home / 'logs'
    logs.mkdir()
    (logs/'marzhavbetone.ru.access.log').write_text('private visitor IP')
    (logs/'marzhavbetone.ru.error.log.1.gz').write_text('private visitor log')
    (logs/'nastoronepodryadchika.ru.access.log').write_text('preserve current log')
    plan = c.main(home, 'plan', fixture=True)
    assert plan['legacy_records']==2 and plan['backup_archives_to_scrub']==2
    try:
        c.main(home, 'apply', 'wrong', fixture=True)
        raise AssertionError('Wrong plan was accepted')
    except RuntimeError as error:
        assert str(error)=='EXACT_PLAN_REQUIRED'
    assert len(list(old.glob('*.json')))==2 and not (home/'nsp-legacy-financial-records').exists()
    result = c.main(home, 'apply', plan['plan_digest'], fixture=True)
    assert result['legacy_contact_record_files_remaining']==0 and not result['financial_minimum_has_contact_fields']
    assert (current/'keep.json').read_bytes()==current_payload
    assert (logs/'marzhavbetone.ru.access.log').read_bytes()==b''
    assert not (logs/'marzhavbetone.ru.error.log.1.gz').exists()
    assert (logs/'nastoronepodryadchika.ru.access.log').read_text()=='preserve current log'
    with zipfile.ZipFile(backup/'copy.zip') as archive:
        assert archive.read('keep.txt')==b'keep-zip-exact' and archive.namelist()==['keep.txt']
    with tarfile.open(backup/'copy.tar.gz') as archive:
        assert archive.extractfile('keep.txt').read()==b'keep-tar-exact'
    minimum = next((home/'nsp-legacy-financial-records').glob('*.json'))
    assert 'private' not in minimum.read_text() and 'email' not in minimum.read_text()
    assert minimum.stat().st_mode&0o777==0o600
    assert minimum.parent.stat().st_mode&0o777==0o700
    assert (backup/rows[0]['id']).exists() is False
    print('EXACT_PLAN_CONTACT_REMOVAL_PRIVATE_FINANCIAL_MINIMUM_ARCHIVES_AND_NEW_DATA_PRESERVED=PASS')

with tempfile.TemporaryDirectory() as temporary:
    home = Path(temporary)
    old = home/'www/marzhavbetone.ru/orders'
    old.mkdir(parents=True)
    (home/'nsp-production-private/orders').mkdir(parents=True)
    path = old/'order_x.json'
    path.write_text(json.dumps({'id':'order_x','status':'paid','total':500000,'email':'customer@example.invalid'}))
    before = path.read_bytes()
    try:
        c.main(home,'plan',fixture=True)
        raise AssertionError('Non-test paid record accepted')
    except RuntimeError as error:
        assert str(error)=='NON_TEST_PAYMENT_REQUIRES_RETENTION_REVIEW'
    assert path.read_bytes()==before
    print('NON_TEST_PAYMENT_STOP_WITHOUT_WRITES=PASS')
