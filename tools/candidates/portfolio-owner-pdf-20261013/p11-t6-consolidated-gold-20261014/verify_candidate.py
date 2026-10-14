#!/usr/bin/env python3
"""Frozen P11/T6 archive-composition gate; no writes, network, Office, or models.
The separate email is never a buyer-archive member. This is not product acceptance.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
import re
import subprocess
import warnings
import zipfile
from pathlib import Path
from typing import Callable

SOURCE = 'fb829b3c4a2f8508b1e655b53edfb4fc541c7ca7'
TREE = '9fed20f17136a306358d04815ae9bb41c810ec3b'
PREFIX = 'tools/candidates/portfolio-owner-pdf-20261013/'
DIRECTORY = PREFIX + 'p11-t6-consolidated-gold-20261014/'
GOLD = PREFIX + 'p11-t6-gold-accent-remediation-20261014/candidates/'
EXPECTED = {
    '00-START-HERE.txt': '2f895a2f2b8ea5e166c8f18dd416465f2651b3562068551fc9f26841fd5dcf3a',
    '50-slovar-poley-raschet-metrami.docx': 'c5de8ebe3b7518042b081894ef0205635f688e3b7160986a0415135e711b601a',
    '51-algoritm-raschet-metrami.pdf': '2a4c98dc4a1b131dbccb787276f487a17a76a0c6643932c0ee0ca666601135d7',
    '52-chek-list-raschet-metrami.docx': '149ff5b2fcb1cfa214a0dfee64f0d6a003bfe3bbbafc60977030a67535b15b33',
    '53-zapros-status-obekta.docx': '4746cd1086be16d55b636ad651370f032956bfda0dfe3f8b83f2f34487774a7a',
    '54-zapros-sostoyanie-escrow.docx': 'bf32807bf9d1ec955cf151f3e5dd055fde47ebd85ce322b0376e0c873f52a319',
    '55-pamyatka-punkt-ustupki-escrow.pdf': '20f65a850db70836b2897dc747ed6478781641e3a4f5a537b094a7afec0814a2',
    '56-pervyy-den-do-podpisi.docx': '9c40a96498037b53a68ecea6f3ee57129a9f2c236d1073d1818c603016260807',
}
GOLD_NUMBERS = {'50', '52', '53', '54'}
ARCHIVE_SHA = 'f365039ef568dbbe9c661a6e1f553d21ddd0b086c9172f1e5a4340fb7dfe7f70'
LETTER_SHA = 'c8f9d78cf2335f2acf52ab8d12258e4e3e799c9c87e3447edcc17c7f0f507ea5'

def require(condition: bool, error: str) -> None:
    if not condition:
        raise ValueError(error)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def assemble(items: list[tuple[str, bytes]]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in items:
            info = zipfile.ZipInfo(name, (2026, 10, 14, 12, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return stream.getvalue()

def manifest_contract(manifest: dict) -> None:
    require(manifest['source_commit'] == SOURCE, 'source commit')
    require(manifest['source_git_tree'] == TREE, 'commit/tree confusion')
    files = manifest['buyer_files']
    require([f['name'] for f in files] == list(EXPECTED), 'selected ordered members')
    require({f['name']: f['sha256'] for f in files} == EXPECTED, 'stale selected SHA')
    for f in files:
        root = GOLD if f['name'][:2] in GOLD_NUMBERS else PREFIX + '13-raschet-metrami/'
        require(f['source_path'] == root + f['name'], 'wrong source path')
        require(f['source_commit'] == SOURCE, 'wrong member commit')
    require(manifest['archive']['path'] == DIRECTORY + 'p11-t6-eight-files-gold-candidate.zip', 'archive path')
    require(manifest['archive']['sha256'] == ARCHIVE_SHA, 'archive SHA anchor')
    require(manifest['limits']['release_authorized'] is False, 'release escalation')
    require(manifest['limits']['G1_G8_accepted_products'] == 0, 'product escalation')
    require(manifest['separate_letter']['in_buyer_archive'] is False, 'email membership')

def archive_contract(data: bytes) -> None:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(z.namelist() == list(EXPECTED), 'archive ordered/unique/root members')
        require(z.testzip() is None, 'archive CRC')
        for name, expected in EXPECTED.items():
            require(sha(z.read(name)) == expected, 'archive member SHA: ' + name)

def letter_references(data: bytes) -> None:
    refs = set(re.findall(r'\b\d{2}-[A-Za-z0-9-]+\.(?:txt|docx|pdf)\b', data.decode('utf-8')))
    require(refs == set(EXPECTED), 'email references')

def verify(manifest: dict, read: Callable[[str], bytes], actual_tree: str) -> dict:
    manifest_contract(manifest)
    require(actual_tree == TREE, 'actual immutable tree')
    items = []
    for f in manifest['buyer_files']:
        data = read(f['source_path'])
        require(sha(data) == f['sha256'] and blob(data) == f['git_blob'] and len(data) == f['bytes'], 'source identity: ' + f['name'])
        items.append((f['name'], data))
    a = manifest['archive']
    archive = read(a['path'])
    require(sha(archive) == ARCHIVE_SHA and blob(archive) == a['git_blob'] and len(archive) == a['bytes'], 'stored archive identity')
    archive_contract(archive)
    require(assemble(items) == archive, 'exact reproducible construction')
    previous = read(a['predecessor_path'])
    require(sha(previous) == a['predecessor_sha256'], 'predecessor identity')
    with zipfile.ZipFile(io.BytesIO(previous)) as z:
        require(z.namelist() == list(EXPECTED) and z.testzip() is None, 'predecessor structure')
        for f, (_, data) in zip(manifest['buyer_files'], items):
            old = z.read(f['name'])
            require(sha(old) == f['previous_sha256'], 'predecessor member SHA')
            require((old != data) == (f['name'][:2] in GOLD_NUMBERS), '4/4 delta boundary')
    e = manifest['separate_letter']
    letter = read(e['path'])
    require(sha(letter) == LETTER_SHA == e['sha256'] and blob(letter) == e['git_blob'] and len(letter) == e['bytes'], 'letter identity')
    letter_references(letter)
    mutations = {}
    def reject(name: str, action: Callable[[], None]) -> None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                action()
        except (ValueError, zipfile.BadZipFile):
            mutations[name] = True
        else:
            raise ValueError('undetected mutation: ' + name)
    bad = copy.deepcopy(manifest)
    bad['buyer_files'][1]['sha256'] = bad['buyer_files'][1]['previous_sha256']
    reject('stale_pre_gold_SHA', lambda: manifest_contract(bad))
    wrong_tree = copy.deepcopy(manifest)
    wrong_tree['source_git_tree'] = SOURCE
    reject('commit_as_tree_SHA', lambda: manifest_contract(wrong_tree))
    release = copy.deepcopy(manifest)
    release['limits']['release_authorized'] = True
    reject('release_escalation', lambda: manifest_contract(release))
    reject('missing_member', lambda: archive_contract(assemble(items[:-1])))
    reject('duplicate_member', lambda: archive_contract(assemble(items + [items[0]])))
    reject('service_letter_in_archive', lambda: archive_contract(assemble(items + [('00-PISMO-POSLE-POKUPKI.txt', letter)])))
    changed = list(items)
    changed[1] = (changed[1][0], changed[1][1] + b'!')
    reject('changed_member_bytes', lambda: archive_contract(assemble(changed)))
    reject('legacy_email_reference', lambda: letter_references(letter.replace(b'56-pervyy-den-do-podpisi.docx', b'01-poryadok-dnya-kogda-prosyat-podpisat.docx')))
    require(len(mutations) == 8 and all(mutations.values()), 'negative coverage')
    return {'status': 'PASS_DETERMINISTIC_CURRENT_CANDIDATE_ONLY', 'members': 8, 'changed_members': 4, 'unchanged_members': 4, 'letter_references': 8, 'archive_sha256': ARCHIVE_SHA, 'negative_mutations_detected': mutations, 'release_authorized': False, 'independent_acceptance': 'NOT_PERFORMED_BY_THIS_SCRIPT'}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    root = parser.parse_args().root.resolve()
    manifest = json.loads((root / DIRECTORY / 'candidate-manifest.json').read_text())
    def git_read(path: str) -> bytes:
        return subprocess.check_output(['git', '-C', str(root), 'show', SOURCE + ':' + path], timeout=10)
    def read(path: str) -> bytes:
        if path == manifest['archive']['path']:
            return (root / path).read_bytes()
        return git_read(path)
    actual_tree = subprocess.check_output(['git', '-C', str(root), 'rev-parse', SOURCE + '^{tree}'], timeout=10).decode().strip()
    print(json.dumps(verify(manifest, read, actual_tree), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
