#!/usr/bin/env python3
"""READ-ONLY integrity/production-drift gate for the approved NSP 32-article candidate.

Never edits production or product files. The source commit is pinned to article
content; metadata-only commits do not invalidate it. Run from repository root.
"""
import argparse
import concurrent.futures
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/editorial/NSP_LEGACY_32_RELEASE_MANIFEST_20261111.json"
MATRIX = ROOT / "docs/editorial/NSP_ALL_43_ARTICLES_MATRIX_20261111.json"
ORIGIN = "https://nastoronepodryadchika.ru/"
HEX = re.compile(r"^[a-f0-9]{64}$")
ARTICLE = re.compile(r"^articles/[a-z0-9-]+\.html$")


def require(condition, error):
    if not condition:
        raise AssertionError(error)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ArticleImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.preview_images = set()

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return
        src = dict(attrs).get("src", "")
        if "document-previews/" not in src:
            return
        raw = src.split("?", 1)[0]
        path = (ROOT / "articles" / raw).resolve()
        require(path.is_relative_to(ROOT / "assets" / "document-previews"),
                "IMAGE_PATH_ESCAPE: " + src)
        require(path.is_file() and not path.is_symlink(),
                "MISSING_PREVIEW: " + src)
        self.preview_images.add(path.relative_to(ROOT).as_posix())


def validate_static():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    require(m["schema"] == "NSP_ARTICLE_ONLY_RELEASE_MANIFEST_v1", "SCHEMA")
    require(m["target_host"] == "nastoronepodryadchika.ru", "TARGET_HOST")
    require(m["release_status"] == "PREFLIGHT_ONLY_NO_PRODUCTION_WRITE", "NOT_DRY_RUN")
    require(m["image_uploads"] == 0, "IMAGE_UPLOADS_NOT_ZERO")
    style = m["style_asset"]
    require(style["path"] == "article.css", "STYLE_SCOPE")
    for key in ("before_sha256", "after_sha256"):
        require(HEX.fullmatch(style[key]) is not None, "STYLE_SHA_FORMAT")
    style_bytes = (ROOT / style["path"]).read_bytes()
    require(sha(style_bytes) == style["after_sha256"], "STYLE_SHA_DRIFT")
    require(len(style_bytes) == style["bytes"], "STYLE_BYTE_DRIFT")
    require(m["cache_busted_stylesheet"] == "article.css?v=nsp32-20261111", "STYLE_CACHE_VERSION")
    files = m["changed_files"]
    protected = m["protected_approved_articles"]
    require(len(files) == 32 and len(protected) == 11, "FILE_COUNTS")
    legacy_expected = {x["path"] for x in matrix["articles"]
                       if x["state"] == "LEGACY_UNREVISED"}
    approved_expected = {x["path"] for x in matrix["articles"]
                         if x["state"] == "APPROVED_V2"}
    paths = [row["path"] for row in files]
    keep = [row["path"] for row in protected]
    require(set(paths) == legacy_expected and len(set(paths)) == 32,
            "LEGACY_EXACT_SET")
    require(set(keep) == approved_expected and len(set(keep)) == 11,
            "APPROVED_EXACT_SET")
    require(not set(paths).intersection(keep), "PROTECTED_OVERLAP")
    for row in files:
        path = row["path"]
        require(ARTICLE.fullmatch(path) is not None, "INVALID_RELEASE_PATH: " + path)
        for k in ("before_sha256", "after_sha256"):
            require(HEX.fullmatch(row[k]) is not None, "INVALID_SHA: " + path)
        p = ROOT / path
        require(p.is_file() and not p.is_symlink(), "MISSING_ARTICLE: " + path)
        data = p.read_bytes()
        require(b"../article.css?v=nsp32-20261111" in data, "STYLE_CACHE_NOT_BUSTED: " + path)
        require(sha(data) == row["after_sha256"], "CANDIDATE_DRIFT: " + path)
        require(len(data) == row["bytes"], "ARTICLE_BYTES: " + path)
        require(row["after_sha256"] != row["before_sha256"],
                "UNEXPECTED_IDENTICAL_ARTICLE: " + path)
    for row in protected:
        require(ARTICLE.fullmatch(row["path"]) is not None, "INVALID_PROTECTED_PATH")
        require(HEX.fullmatch(row["sha256"]) is not None, "INVALID_PROTECTED_HASH")
    images = set()
    for path in paths:
        parser = ArticleImages()
        parser.feed((ROOT / path).read_text(encoding="utf-8"))
        require(len(parser.preview_images) >= 1, "NO_PREVIEWS: " + path)
        images.update(parser.preview_images)
    require(len(images) == m["image_paths_http_200_verified"] == 33,
            "PREVIEW_SET_CHANGED")
    return m, sorted(images)


def get_live(path, limit=200_000):
    req = urllib.request.Request(
        ORIGIN + path,
        headers={"Accept-Encoding": "identity", "Cache-Control": "no-cache",
                 "User-Agent": "NSP-Editorial-Release-Gate/1.0"},
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        require(response.status == 200, "HTTP_NOT_200: " + path)
        if path.startswith("assets/document-previews/"):
            require(response.headers.get_content_type() == "image/jpeg",
                    "MEDIA_CONTENT_TYPE: " + path)
            header = response.read(4)
            require(header[:3] == b"\xff\xd8\xff", "MEDIA_JPEG_MAGIC: " + path)
            return header
        data = response.read(limit + 1)
        require(len(data) <= limit, "LIVE_TOO_LARGE: " + path)
        return data


def validate_live(m, images, mode):
    keys = "before_sha256" if mode == "live-pre" else "after_sha256"
    checks = [(r["path"], r[keys]) for r in m["changed_files"]]
    checks += [(r["path"], r["sha256"]) for r in m["protected_approved_articles"]]
    style = m["style_asset"]
    checks.append((style["path"],
                   style["before_sha256"] if mode == "live-pre" else style["after_sha256"]))
    media = [(path, None) for path in images]
    def inspect(row):
        path, expected = row
        try:
            content = get_live(path)
            actual = sha(content)
            require(expected is None or actual == expected,
                    "LIVE_HASH_DRIFT: " + path + " expected=" + str(expected) +
                    " actual=" + actual)
            return path
        except Exception as exc:
            raise RuntimeError("LIVE_PREFLIGHT_FAIL: " + path + ": " + str(exc)) from exc
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        # map preserves deterministic failure order and provides a bounded URL count.
        result = list(pool.map(inspect, checks + media))
    require(len(result) == 77, "LIVE_CHECK_COUNT")
    return len(result)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("static", "live-pre", "live-post"),
                    default="static")
    args = ap.parse_args()
    m, images = validate_static()
    live_count = validate_live(m, images, args.mode) if args.mode != "static" else 0
    print(json.dumps({
        "status": "PASS", "mode": args.mode,
        "article_candidates": len(m["changed_files"]),
        "protected_articles": len(m["protected_approved_articles"]),
        "images_already_on_site": len(images),
        "live_checked": live_count,
        "production_writes": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(1)
