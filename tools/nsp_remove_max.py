#!/usr/bin/env python3
"""Remove MAX links only; preserve every unrelated byte and contact."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from html.parser import HTMLParser

HOST = re.compile(r'(?i)^(?:https?:)?//(?:www\.)?max\.ru(?:[/?#]|$)')
ANCHOR = re.compile(r'<a\b[^>]*\bhref\s*=\s*([\"\'])(?:https?:)?//(?:www\.)?max\.ru(?:[/?#][^\"\']*)?\1[^>]*>.*?</a\s*>', re.I | re.S)
SAME_AS = re.compile(r'("sameAs"\s*:\s*\[)([^\]]*)(\])', re.S)
TOKEN = r'"(?:https?:)?//(?:www\.)?max\.ru(?:[/?#][^"\r\n]*)?"'
LD = re.compile(r'<script\b[^>]*type\s*=\s*[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script\s*>', re.I | re.S)
FILES = ('index.html', 'katalog.html')

class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            values = dict(attrs)
            if 'href' in values:
                self.links.append(values['href'])

def links(text):
    parser = Links(); parser.feed(text); parser.close()
    return parser.links

def transform(text):
    before = links(text)
    result, count = ANCHOR.subn('', text)
    def clean_same_as(match):
        body = match.group(2)
        body = re.sub(r'\s*' + TOKEN + r'\s*,', '', body, flags=re.I)
        body = re.sub(r',\s*' + TOKEN + r'\s*', '', body, flags=re.I)
        body = re.sub(r'^\s*' + TOKEN + r'\s*$', '', body, flags=re.I)
        return match.group(1) + body + match.group(3)
    result = SAME_AS.sub(clean_same_as, result)
    assert links(result) == [x for x in before if not HOST.match(x)], 'OTHER_LINKS_CHANGED'
    assert not any(HOST.match(x) for x in links(result)), 'MAX_LINK_REMAINS'
    for block in LD.findall(result):
        json.loads(block)
    assert not re.search(r'(?i)(?:https?:)?//(?:www\.)?max\.ru(?:[/?#\"\']|$)', result), 'MAX_REFERENCE_REMAINS'
    assert ANCHOR.sub('', result) == result, 'NOT_IDEMPOTENT'
    return result, count

def self_test():
    for values in [
        ['https://max.ru/a','https://t.me/a'],
        ['https://t.me/a','https://max.ru/a','https://dzen.ru/a'],
        ['https://t.me/a','https://max.ru/a'],
        ['https://max.ru/a'],
        ['https://max.ru/a','https://max.ru/b','https://t.me/a'],
        [],
    ]:
        text = '<style>.x{max-width:800px}</style><script type="application/ld+json">' + json.dumps({'sameAs':values}) + '</script><a href="https://t.me/a">TG</a><a href="https://max.ru/a" aria-label="MAX"><svg><path d="x"/></svg></a><a href="mailto:nastoronepodryadchika@yandex.ru">Email</a>'
        actual, count = transform(text)
        assert count == 1
        assert json.loads(LD.search(actual).group(1))['sameAs'] == [v for v in values if not HOST.match(v)]
        assert '.x{max-width:800px}' in actual
        assert transform(actual)[0] == actual
    for href in ['https://max.ru/a', 'https://www.max.ru/a', '//max.ru/a', 'http://max.ru/a']:
        actual, count = transform("<a href='" + href + "'>MAX</a><a href='https://max.ru.example/a'>untouched</a>")
        assert count == 1 and actual == "<a href='https://max.ru.example/a'>untouched</a>"
    print('REMOVE_MAX_SELF_TESTS=PASS (10 cases)')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    self_test()
    if args.self_test and args.root is None:
        raise SystemExit(0)
    if args.root is None:
        parser.error('root required')
    prepared, manifest = {}, []
    for name in FILES:
        path = args.root / name
        if path.is_symlink() or not path.is_file():
            raise SystemExit('MISSING_OR_SYMLINK_' + name)
        original = path.read_bytes()
        changed, count = transform(original.decode('utf-8'))
        data = changed.encode('utf-8')
        prepared[name] = data
        manifest.append({'path':name,'before':hashlib.sha256(original).hexdigest(),'after':hashlib.sha256(data).hexdigest(),'links_removed':count,'changed':original != data})
    for name, data in prepared.items():
        (args.root / name).write_bytes(data)
    if args.manifest:
        args.manifest.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))
    print('REMOVE_MAX_DOCUMENTS=PASS')
