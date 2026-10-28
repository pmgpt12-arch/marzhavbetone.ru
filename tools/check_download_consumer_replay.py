#!/usr/bin/env python3
"""Verify the actual consumer record() in an in-memory DB; no live service calls."""
import argparse
import ast
import contextlib
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import types


def check(root):
    paths = {name: root / 'app' / name for name in ('events.py', 'db.py', 'connector.py')}
    raw = {name: path.read_text() for name, path in paths.items()}
    schema = re.search(r'CREATE TABLE IF NOT EXISTS events\s*\(.*?\);', raw['db.py'], re.S).group(0)
    index = next(node.value for node in ast.walk(ast.parse(raw['db.py']))
                 if isinstance(node, ast.Constant) and isinstance(node.value, str)
                 and node.value.startswith('CREATE UNIQUE INDEX IF NOT EXISTS events_uuid'))
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript(schema)
    conn.execute(index)
    @contextlib.contextmanager
    def connection():
        yield conn
        conn.commit()
    package = types.ModuleType('_download_consumer_fixture')
    package.__path__ = []
    db = types.ModuleType('_download_consumer_fixture.db')
    db.connection = connection
    sys.modules[package.__name__] = package
    sys.modules[db.__name__] = db
    events = types.ModuleType('_download_consumer_fixture.events')
    events.__package__ = package.__name__
    exec(compile(raw['events.py'], str(paths['events.py']), 'exec'), events.__dict__)
    handler = next(n for n in ast.parse(raw['connector.py']).body
                   if isinstance(n, ast.FunctionDef) and n.name == '_ingest_funnel')
    forwarded = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == 'record' and any(k.arg == 'event_uuid' for k in n.keywords)
                    for n in ast.walk(handler))
    assert forwarded, 'ingestion stopped forwarding event identity'
    uid = '9a3192aa-1cab-44a1-8a1b-a972e5330c92'
    payload = {'event_uuid': uid, 'occurred_at': '2026-10-23T00:00:00+00:00', 'sku': 'p3', 'source': 'site'}
    first = events.record('funnel.product_delivered', payload=payload, event_uuid=uid)
    replay = events.record('funnel.product_delivered', payload=payload, event_uuid=uid)
    assert first['id'] == replay['id']
    assert conn.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 1
    other = '0a3192aa-1cab-44a1-8a1b-a972e5330c92'
    events.record('funnel.product_delivered', payload={**payload, 'event_uuid': other}, event_uuid=other)
    assert conn.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 2
    conn.close()
    return {'status': 'PASS', 'consumer_file_sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest()
             for name, path in paths.items()}, 'database': ':memory:', 'live_database_modified': False,
            'network_requests': 0, 'identical_uuid_attempts': 2, 'identical_uuid_event_rows': 1,
            'different_uuid_total_rows': 2, 'ingestion_forwards_uuid': forwarded,
            'scope': 'actual record() and actual unique index; no live receiver acceptance claimed'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--consumer-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = check(args.consumer_root)
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text)
