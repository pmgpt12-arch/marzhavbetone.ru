#!/usr/bin/env python3
"""Permit one observed LAN peer to GET only the nonsecret Office bootstrap."""
from pathlib import Path
from hashlib import sha256
import argparse, importlib.util, json, py_compile

NEEDLE = '        if self.client_address[0] not in ALLOWED:\n'
INSERT = '''        # Bootstrap download only: the owner's observed LAN download peer.
        # Job/input/result/config access keeps the existing IP and token checks.
        if (self.command == 'GET' and self.path == '/finish-office.ps1'
                and self.client_address[0] == '192.168.1.71'):
            return True
'''


def gate(path):
    spec = importlib.util.spec_from_file_location('office_transport_bootstrap_gate', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.ALLOWED == {'192.168.1.140', '192.168.1.72', '127.0.0.1'}
    cases = [('192.168.1.71', 'GET', '/finish-office.ps1', True),
             ('192.168.1.71', 'POST', '/finish-office.ps1', False),
             ('192.168.1.71', 'GET', '/native/current.xml', False),
             ('192.168.1.71', 'GET', '/word/current.xml', False),
             ('192.168.1.71', 'GET', '/config.xml', False),
             ('192.168.1.71', 'GET', '/finish-office.ps1?x=1', False),
             ('192.168.1.71', 'GET', '/finish-office.ps1/../config.xml', False),
             ('192.168.1.99', 'GET', '/finish-office.ps1', False),
             ('192.168.1.140', 'GET', '/native/current.xml', True)]
    for peer, method, route, expected in cases:
        handler = object.__new__(module.Handler)
        handler.connection = type('Connection', (), {'settimeout': lambda self, v: None})()
        handler.client_address = (peer, 1234); handler.command = method; handler.path = route
        errors = []; handler.send_error = lambda code: errors.append(code)
        result = handler.authorized()
        assert result is expected and errors == ([] if expected else [403]), (peer, method, route)
    return len(cases)


def run(root, evidence):
    target = root / 'transport.py'; before = target.read_bytes(); text = before.decode()
    assert text.count(NEEDLE) == 1 and INSERT not in text
    assert 'self.respond((ROOT/\'finish-office.ps1\').read_bytes()' in text
    patched = text.replace(NEEDLE, INSERT + NEEDLE)
    assert patched.replace(INSERT, '') == text
    compile(patched, str(target), 'exec')
    backup = root / 'transport.before-bootstrap-peer-20261020.py'
    assert not backup.exists(); backup.write_bytes(before)
    try:
        target.write_text(patched)
        py_compile.compile(str(target), doraise=True)
        count = gate(target)
    except BaseException:
        target.write_bytes(before); raise
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps({'status': 'STATIC_GATE_PASS_SERVICE_RESTART_PENDING',
        'cause': 'Observed HTTP 403 for GET /finish-office.ps1 from 192.168.1.71 at 06:29 Krasnoyarsk; existing peer guard excludes that address.',
        'scope': 'Only exact GET /finish-office.ps1 for that peer; existing global peers, job/input/result routes and token checks unchanged.',
        'before_sha256': sha256(before).hexdigest(), 'after_sha256': sha256(target.read_bytes()).hexdigest(),
        'regression_cases': count, 'office_capability': 'NOT_YET_QUALIFIED'}, ensure_ascii=False, indent=2) + '\n')
    print('BOOTSTRAP_ROUTE_GATE_PASS', count, sha256(target.read_bytes()).hexdigest())


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True); a = p.parse_args(); run(a.root, a.evidence)
