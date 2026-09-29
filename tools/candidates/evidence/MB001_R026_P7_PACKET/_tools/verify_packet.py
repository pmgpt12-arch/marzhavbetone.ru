#!/usr/bin/env python3
"""Проверка готовности пакета P7 (Р-026) перед коммитом.

    python3 …/_tools/verify_packet.py --pr-head-sha <sha>            # показать
    python3 …/_tools/verify_packet.py --pr-head-sha <sha> --write    # и вписать вывод в отчёт
    python3 …/_tools/verify_packet.py --pr-head-sha <sha> --post-commit  # плюс чистое дерево

Проверки:
  1. список и SHA-256 в отчёте = заново собранный mvb_build_product_zip('p7');
  2. у каждой записи ZIP есть строка индекса и файл извлечения с тем же SHA-256;
  3. пути и строки, на которые ссылаются отчёт и карты, существуют в текущем дереве;
  4. в авторском тексте отчёта и карт нет правовых оценок и рекомендаций;
  5. изменения относительно головы PR — только файлы пакета;
  6. (--post-commit) рабочее дерево чистое.
Код возврата 0 — все проверки пройдены.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PACKET = TOOLS.parent
ROOT = PACKET.parents[3]
REPORT = ROOT / "tools/candidates/MB001_R026_P7_REVIEW_PACKET.md"
REPORT_REL = "tools/candidates/MB001_R026_P7_REVIEW_PACKET.md"
PACKET_REL = "tools/candidates/evidence/MB001_R026_P7_PACKET"
KIT = ROOT / "products-storage/03-dogovor-podryada"

# Слова правовой оценки и рекомендации. Раздел 1 отчёта называет режим
# («оценок „верно / неверно“ нет») и из проверки исключён; тексты в блоках
# ``` — цитаты выдаваемых файлов, а не авторский текст.
VERDICT = re.compile(
    r"(?i)\b(?:не)?верн(?:о|ый|ая|ое|ые|а)\b|соответству|рекоменд|следует\s+(?:исправ|измен|замен|удал)"
    r"|(?:не)?законн|недействител|наруша|противореч|(?:не)?допустим|ошибочн|надо\s+исправ|нужно\s+исправ"
    r"|правомерн|ничтожн")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def section(text: str, n: int) -> str:
    m = re.search(rf"^## {n}\..*?(?=^## {n + 1}\.|\Z)", text, flags=re.M | re.S)
    return m.group(0) if m else ""


def check_zip(report: str) -> tuple[bool, list[str]]:
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        res = subprocess.run(["php", str(TOOLS / "build_p7.php"), str(ROOT), tmp],
                             capture_output=True, text=True)
        if res.returncode != 0:
            return False, [f"PHP-сборка не прошла: {res.stderr.strip()}"]
        zpath = Path(res.stdout.strip().splitlines()[-1])
        zbytes = zpath.read_bytes()
        with zipfile.ZipFile(zpath) as z:
            fresh = {i.filename: (i.file_size, sha256(z.read(i.filename))) for i in z.infolist()}
    s3 = section(report, 3)
    rows = re.findall(r"^\| \d+ \| `([^`]+)` \| \w+ \| (\d+) \| `([0-9a-f]{64})` \|", s3, flags=re.M)
    listed = {n: (int(size), h) for n, size, h in rows}
    ok = True
    if sorted(listed) != sorted(fresh):
        ok = False
        out.append(f"состав различается: в отчёте {sorted(listed)}, собрано {sorted(fresh)}")
    for n, v in fresh.items():
        if listed.get(n) != v:
            ok = False
            out.append(f"{n}: в отчёте {listed.get(n)}, собрано {v}")
    arch = re.search(r"Архив: `[^`]+`, (\d+) байт, SHA-256 `([0-9a-f]{64})`", s3)
    arch_same = bool(arch) and arch.group(2) == sha256(zbytes) and int(arch.group(1)) == len(zbytes)
    out.append(f"записей собрано {len(fresh)}, в отчёте {len(listed)}; SHA-256 и размеры записей "
               f"{'совпали' if ok else 'РАСХОДЯТСЯ'}; SHA-256 архива {sha256(zbytes)[:16]}… "
               f"{'= отчёт' if arch_same else '≠ отчёт'}")
    return ok and arch_same, out


def check_index(report: str) -> tuple[bool, list[str]]:
    s3 = section(report, 3)
    names = re.findall(r"^\| \d+ \| `([^`]+)` \|", s3, flags=re.M)
    hashes = dict(re.findall(r"^\| \d+ \| `([^`]+)` \| \w+ \| \d+ \| `([0-9a-f]{64})`", s3, flags=re.M))
    s4 = section(report, 4)
    idx = dict(re.findall(r"^\| `([^`]+)` \| \w+ \| .*? \| `([^`]+)` \|$", s4, flags=re.M))
    ok, out = True, []
    for n in names:
        ev = idx.get(n)
        if not ev:
            ok = False
            out.append(f"{n}: нет строки индекса")
            continue
        p = ROOT / ev
        if not p.is_file():
            ok = False
            out.append(f"{n}: нет файла извлечения {ev}")
            continue
        head = p.read_text(encoding="utf-8")[:400]
        m = re.search(r"sha256: ([0-9a-f]{64})", head)
        if not m or m.group(1) != hashes.get(n):
            ok = False
            out.append(f"{n}: SHA-256 в извлечении не равен строке раздела 3")
    out.append(f"записей в разделе 3: {len(names)}; строк индекса: {len(idx)}; "
               f"у всех есть извлечение с тем же SHA-256: {'да' if ok else 'нет'}")
    return ok, out


PATH_TOKEN = re.compile(r"`([\w./-]+?\.(?:py|php|md|html|txt|docx|xlsx|pdf|json)|[\w./-]+/)(?::(\d+)(?:-(\d+))?)?`")


def check_links(texts: dict[str, str]) -> tuple[bool, list[str]]:
    tracked = set(git("ls-files").splitlines())
    ok, out, seen, at_commit = True, [], 0, []
    for src, text in texts.items():
        for m in PATH_TOKEN.finditer(text):
            token, a, b = m.group(1), m.group(2), m.group(3)
            if "/" not in token.rstrip("/"):
                cand = [ROOT / token, KIT / token, TOOLS / token, PACKET / token]
            else:
                cand = [ROOT / token]
            path = next((c for c in cand if c.exists()), None)
            seen += 1
            if path is None:
                # Файл вне текущего дерева, названный вместе с коммитом, проверяется в этом коммите
                line = text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.end())]
                shas = re.findall(r"\b[0-9a-f]{40}\b", line)
                if any(subprocess.run(["git", "cat-file", "-e", f"{s}:{token}"], cwd=ROOT).returncode == 0
                       for s in shas):
                    at_commit.append(token)
                    continue
                ok = False
                out.append(f"{src}: нет пути `{token}`")
                continue
            if path.is_file() and a:
                n = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
                if int(b or a) > n or int(a) < 1:
                    ok = False
                    out.append(f"{src}: `{token}:{a}{'-' + b if b else ''}` — в файле {n} строк")
            rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else token
            if path.is_file() and not rel.startswith(PACKET_REL) and rel != REPORT_REL and rel not in tracked:
                ok = False
                out.append(f"{src}: `{rel}` не отслеживается git")
    out.append(f"ссылок на пути проверено: {seen}; все существуют в текущем дереве: {'да' if ok else 'нет'}"
               + (f"; вне дерева, но в названном рядом коммите: {', '.join(sorted(set(at_commit)))}" if at_commit else ""))
    return ok, out


def authored(report: str) -> str:
    body = re.sub(r"^```.*?^```", "", report, flags=re.M | re.S)
    body = body.replace(section(report, 1), "")
    return re.sub(r"<!-- VERIFY:BEGIN -->.*?<!-- VERIFY:END -->", "", body, flags=re.S)


def check_verdicts(texts: dict[str, str]) -> tuple[bool, list[str]]:
    ok, out = True, []
    for src, text in texts.items():
        for i, line in enumerate(text.splitlines(), 1):
            if VERDICT.search(line):
                ok = False
                out.append(f"{src}:{i}: {line[:160]}")
    out.append(f"слов правовой оценки и рекомендаций в авторском тексте: {'нет' if ok else 'ЕСТЬ'} "
               f"(проверено: {', '.join(texts)}; раздел 1 и блоки ``` исключены)")
    return ok, out


def check_diff(pr_head: str, post: bool) -> tuple[bool, list[str]]:
    changed = set(git("diff", "--name-only", pr_head, "HEAD").split())
    status = [l[3:] for l in git("status", "--porcelain", "--untracked-files=all").splitlines()]
    allowed = lambda p: p == REPORT_REL or p.startswith(PACKET_REL + "/")
    everything = changed | set(status)
    bad = sorted(p for p in everything if not allowed(p))
    out = [f"изменено относительно {pr_head[:7]} (коммиты + рабочее дерево): {len(everything)} файлов; "
           f"вне пакета: {len(bad)}" + (f" — {bad}" if bad else "")]
    ignored = [l[3:] for l in git("status", "--porcelain", "--ignored", "--untracked-files=all", "--",
                                  PACKET_REL, REPORT_REL).splitlines() if l.startswith("!!")]
    out.append(f"файлов пакета под .gitignore (не попали бы в коммит): {len(ignored)}"
               + (f" — {ignored}" if ignored else ""))
    ok = not bad and not ignored
    if post:
        clean = not status
        out.append(f"рабочее дерево после коммита чистое: {'да' if clean else 'нет'}")
        ok = ok and clean
    return ok, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr-head-sha", required=True)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--post-commit", action="store_true")
    args = ap.parse_args()

    report = REPORT.read_text(encoding="utf-8")
    maps = {str(p.relative_to(ROOT)): p.read_text(encoding="utf-8") for p in sorted((PACKET / "maps").glob("*.md"))}
    link_texts = {REPORT_REL: re.sub(r"<!-- VERIFY:BEGIN -->.*?<!-- VERIFY:END -->", "", report, flags=re.S), **maps}
    verdict_texts = {REPORT_REL: authored(report), **maps}

    results = [
        ("1. Список и SHA-256 = заново собранный ZIP p7", *check_zip(report)),
        ("2. Каждый файл архива есть в индексе", *check_index(report)),
        ("3. Ссылки отчёта и карт существуют в текущем дереве", *check_links(link_texts)),
        ("4. Нет правовых вердиктов и рекомендаций", *check_verdicts(verdict_texts)),
        ("5. Изменения — только пакет материалов", *check_diff(args.pr_head_sha, args.post_commit)),
    ]
    lines = []
    for title, ok, details in results:
        lines.append(f"- {'PASS' if ok else 'FAIL'} — {title}")
        lines += [f"  - {d}" for d in details]
    all_ok = all(ok for _, ok, _ in results)
    lines.append(f"- Итог: {'PASS' if all_ok else 'FAIL'} "
                 f"({sum(ok for _, ok, _ in results)}/{len(results)})")
    print("\n".join(lines))
    if args.write:
        block = "<!-- VERIFY:BEGIN -->\n" + "\n".join(lines) + "\n<!-- VERIFY:END -->"
        new = re.sub(r"<!-- VERIFY:BEGIN -->.*?<!-- VERIFY:END -->", lambda _: block, report, flags=re.S)
        REPORT.write_text(new, encoding="utf-8")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
