#!/usr/bin/env python3
"""Exact legacy HTTP acceptance with a narrow observed CDN transformation list.
Origin SHA remains mandatory. No stripping of prices, routes, headings or text.
Evidence: legacy-http-diagnosis.json, run 39408736540.
"""
from __future__ import annotations
import hashlib,html,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D=Path(__file__).resolve().parent
HREF=re.compile(r'href="/cdn-cgi/l/email-protection#([a-fA-F0-9]+)"')
SPAN=re.compile(r'<span class="__cf_email__" data-cfemail="([a-fA-F0-9]+)">\[email&#160;protected\]</span>')
DECODE=re.compile(r'<script data-cfasync="false" src="/cdn-cgi/scripts/[a-f0-9]{8}/cloudflare-static/email-decode\.min\.js"></script>')
BEACON=re.compile(r'^<script type="module" src="https://static\.cloudflareinsights\.com/beacon\.min\.js/[A-Za-z0-9]+" integrity="sha512-[A-Za-z0-9+/=]+" data-cf-beacon=\'([^\'\n]+)\' crossorigin="anonymous"></script>\n',re.M)


def decode_email(value):
    b=bytes.fromhex(value)
    assert len(b)>2,'CDN_EMAIL_PAYLOAD_INVALID'
    value=bytes(x^b[0] for x in b[1:]).decode('utf-8')
    assert '@' in value and not any(c in value for c in '\r\n<>"'),'CDN_EMAIL_NOT_ADDRESS'
    return value


def normalize(data):
    text=data.decode('utf-8')
    text,hrefs=HREF.subn(lambda m:'href="mailto:'+html.escape(decode_email(m.group(1)),quote=True)+'"',text)
    text,spans=SPAN.subn(lambda m:html.escape(decode_email(m.group(1)),quote=False),text)
    text,decoders=DECODE.subn('',text)
    def remove_beacon(match):
        cfg=json.loads(match.group(1))
        assert set(cfg)=={'version','token','r','spa'},'CDN_BEACON_SCHEMA_CHANGED'
        assert re.fullmatch(r'[a-f0-9]{32}',cfg['token']) and cfg['r']==1 and cfg['spa']==2,'CDN_BEACON_PARAMETERS_CHANGED'
        assert isinstance(cfg['version'],str) and re.fullmatch(r'[0-9.]+',cfg['version']),'CDN_BEACON_VERSION_CHANGED'
        return ''
    text,beacons=BEACON.subn(remove_beacon,text)
    assert hrefs<=2 and spans<=1 and decoders<=1 and beacons<=1,'CDN_TRANSFORM_COUNT_CHANGED'
    return text.encode('utf-8'),{'email_links_decoded':hrefs,'email_spans_decoded':spans,
      'email_decoder_removed':decoders,'cloudflare_beacon_removed':beacons}


def verify(data,source):
    normalized,changes=normalize(data)
    actual=hashlib.sha256(normalized).hexdigest();expected=hashlib.sha256(source).hexdigest()
    assert normalized==source,'LEGACY_HTTP_CONTENT_CHANGED_AFTER_EXACT_CDN_DECODE'
    return {'status':'PASS_EXACT_ORIGIN_CONTENT_WITH_OBSERVED_CDN_TRANSFORMS',
      'raw_http_sha256':hashlib.sha256(data).hexdigest(),'normalized_sha256':actual,
      'expected_origin_sha256':expected,'transformations':changes,'all_business_content_compared_byte_exact':True}


def self_test(source):
    def encode(value,key):return bytes([key]+[x^key for x in value.encode()]).hex()
    mail='marzhavbetone@yandex.ru'
    assert source.count(('href="mailto:'+mail+'"').encode())==2
    text=source.decode().replace('href="mailto:'+mail+'"','href="/cdn-cgi/l/email-protection#'+encode(mail,87)+'"')
    text=text.replace('>'+mail+'</a>','><span class="__cf_email__" data-cfemail="'+encode(mail,29)+'">[email&#160;protected]</span></a>',1)
    text=text.replace('<script src="app-script.php?v=21"></script>',
      '<script data-cfasync="false" src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script><script src="app-script.php?v=21"></script>',1)
    beacon='<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js/vtest" integrity="sha512-YWJjZA==" data-cf-beacon=\'{"version":"2024.11.0","token":"00000000000000000000000000000000","r":1,"spa":2}\' crossorigin="anonymous"></script>\n'
    text=text.replace('</body>',beacon+'</body>',1)
    verify(text.encode(),source);verify(source,source)
    assert 'data-price="2990000"' in text and '<h1>' in text and 'href="/' in text
    negatives=[
      text.replace('data-price="2990000"','data-price="2990001"',1),
      text.replace('<h1>','<h1>UNAPPROVED ',1),
      text.replace('href="/','href="/wrong/',1),
      text.replace(encode(mail,29),encode('wrong@example.invalid',29),1),
      text.replace('</body>','<script src="/unapproved.js"></script></body>',1)]
    for candidate in negatives:
        try:verify(candidate.encode(),source)
        except (AssertionError,ValueError):pass
        else:raise AssertionError('CDN_GATE_NEGATIVE_FIXTURE_NOT_DETECTED')
    return {'positive_fixtures':2,'negative_mutations_rejected':len(negatives)}


if __name__=='__main__':
    c=json.loads((D/'contract.json').read_text())
    source=subprocess.check_output(['git','show',c['approved_base_commit']+':index.html'],cwd=ROOT,timeout=15)
    print('LEGACY_CDN_GATE_TEST',json.dumps(self_test(source)))
