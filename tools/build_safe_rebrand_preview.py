#!/usr/bin/env python3
"""Build a commerce-disabled, noindex design preview from approved public HTML.

The public root and all payment endpoints stay untouched. Output contains only
HTML/CSS/public images and a local navigation helper. No PHP, sales scripts,
analytics, forms or customer records are shipped.

    python3 tools/build_safe_rebrand_preview.py --output /tmp/mb-brand-preview

The preview is for visual verification only, NOT a payment/staging acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "/rebrand-preview-20261016/"
PAGE = re.compile(r"<body\b[^>]*>", re.I)
SCRIPTS = re.compile(r"\s*<script\b[^>]*>[\s\S]*?</script>", re.I)
CANONICAL = re.compile(r'\s*<link\b[^>]*rel="canonical"[^>]*>', re.I)
META_OG = re.compile(r'\s*<meta\b[^>]*\bproperty="og:[^"]*"[^>]*>', re.I)
RSS_LINK = re.compile(r'\s*<link\b[^>]*rel="alternate"[^>]*type="application/rss\+xml"[^>]*>', re.I)
ABS_URL = re.compile(r'\b(href|src|action|poster)="(/[^"]*)"', re.I)
FORM = re.compile(r'<form\b',re.I)
HEAD_CLOSE = re.compile(r"</head>", re.I)
BODY_CLOSE = re.compile(r"</body>", re.I)
SKIP_FOLDERS = {".git", "node_modules", ".claude", "content", "data", "tools"}

BANNER = (
    '<div class="preview-only-banner" role="note">'
    '<b>Предпросмотр нового сайта</b> · «На стороне подрядчика». '
    'Оплата, отправка заявок и сбор данных отключены.'
    '</div>'
)
INLINE = '''
<style>
.preview-only-banner{position:relative;z-index:999;padding:12px 18px;
 background:#24292F;color:white;text-align:center;font:600 13px/1.45 Arial,sans-serif}
.preview-only-banner b{color:#D2B88B}
button.add-to-cart,button.cart-toggle,button.checkout-submit,
form button,button[type="submit"]{opacity:.5!important;cursor:not-allowed!important}
.preview-disabled{pointer-events:none!important}
</style>
'''
NAV_HELPER = """(function(){
  document.addEventListener('DOMContentLoaded',function(){
    const header=document.querySelector('.topbar,.article-nav');
    const nav=header&&header.querySelector('nav[aria-label="Основная навигация"],nav.links');
    if(header&&nav&&!header.querySelector('.nav-toggle')){
      const button=document.createElement('button');
      button.type='button';button.className='nav-toggle';
      button.setAttribute('aria-label','Меню');
      button.setAttribute('aria-expanded','false');
      button.appendChild(document.createElement('span'));
      button.addEventListener('click',function(){
        const open=nav.classList.toggle('is-open');
        button.setAttribute('aria-expanded',String(open));
      });
      nav.addEventListener('click',function(e){
        if(e.target.closest('a')){nav.classList.remove('is-open');button.setAttribute('aria-expanded','false');}
      });
      header.appendChild(button);
    }
    document.querySelectorAll('form').forEach(function(f){f.addEventListener('submit',function(e){e.preventDefault()},true)});
    document.querySelectorAll('button.add-to-cart,button.cart-toggle').forEach(function(b){b.disabled=true});
  });
})();"""


def tracked_public_html() -> list[Path]:
    result=subprocess.run(["git","ls-files","--","*.html"],cwd=ROOT,
                          text=True,capture_output=True,check=True,timeout=12)
    names=[]
    for entry in result.stdout.splitlines():
        p=Path(entry)
        if not set(p.parts)&SKIP_FOLDERS and (ROOT/p).is_file():
            names.append(p)
    return names


def rewrite_absolute(match: re.Match[str]) -> str:
    attribute, link = match.groups()
    if link.startswith("//"):
        return match.group(0)
    return f'{attribute}="{PREFIX}{link.lstrip("/")}"'


def prepare_html(text: str, file: Path) -> str:
    if PAGE.search(text) is None or HEAD_CLOSE.search(text) is None:
        raise ValueError(f"Invalid public HTML structure: {file}")
    text = SCRIPTS.sub("", text)
    text = CANONICAL.sub("", text)
    text = META_OG.sub("", text)
    text = RSS_LINK.sub("", text)
    text = ABS_URL.sub(rewrite_absolute, text)
    text = FORM.sub('<form onsubmit="return false"', text)
    text = HEAD_CLOSE.sub(
        '<meta name="robots" content="noindex,nofollow,noarchive">\n'
        + INLINE + '</head>', text, count=1)
    text = PAGE.sub(lambda match: match.group(0)+"\n"+BANNER, text, count=1)
    text = BODY_CLOSE.sub(f'<script defer src="{PREFIX}preview-nav.js"></script></body>',text,count=1)
    if "app-script.php" in text or "<script src" in text.replace("preview-nav.js", ""):
        raise ValueError(f"Disallowed commerce script on {file}")
    return text


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    destination=args.output.resolve()
    if destination.exists():
        raise ValueError(f"Refusing to overwrite prior preview {destination}")
    public=tracked_public_html()
    if len(public)!=88:
        raise ValueError(f"Expected 88 public HTML files, got {len(public)}")
    destination.mkdir(parents=True)
    copied=[]
    for rel in public:
        target=destination/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(prepare_html((ROOT/rel).read_text("utf-8"),rel),encoding="utf-8")
        copied.append(rel.as_posix())
    for css in ROOT.glob("*.css"):
        shutil.copyfile(css,destination/css.name)
        copied.append(css.name)
    for name in ["favicon.svg","favicon.ico","favicon-32.png","apple-touch-icon.png"]:
        candidate=ROOT/name
        if candidate.exists():
            shutil.copyfile(candidate,destination/name)
            copied.append(name)
    for image in sorted((ROOT/"assets").rglob("*")):
        if image.is_file():
            rel=image.relative_to(ROOT)
            target=destination/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(image,target)
            copied.append(rel.as_posix())
    (destination/"preview-nav.js").write_text(NAV_HELPER,encoding="utf-8")
    copied.append("preview-nav.js")
    manifest={
        "kind":"VISUAL_ONLY_DISABLED_COMMERCE",
        "prefix":PREFIX,
        "html_pages":len(public),
        "files":{name:hashlib.sha256((destination/name).read_bytes()).hexdigest()
                 for name in sorted(copied)},
        "assertions":["no PHP or buyer/order files","no site analytics","forms disabled",
                      "noindex all HTML","not production checkout tested"],
    }
    (destination/"preview-manifest.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if any(x.suffix==".php" for x in destination.rglob("*")):
        raise ValueError("PHP found in visual-only preview")
    print(json.dumps({"path":str(destination),"html":len(public),
                      "files":len(copied),"prefix":PREFIX,
                      "manifest_sha256":hashlib.sha256(
                          (destination/"preview-manifest.json").read_bytes()).hexdigest()}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
