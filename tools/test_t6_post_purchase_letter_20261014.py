#!/usr/bin/env python3
"""Read-only author checks for the owner-authorized P11/T6 email source.
Frozen source: PR 625 at d961b9c7c95b45919ef96347e5a0d27f4d6f0fcc.
No Office, model, network, archive build, or production operation.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

LETTER = "tools/candidates/portfolio-owner-pdf-20261013/19-kvartiry-vmesto-deneg/00-PISMO-POSLE-POKUPKI.txt"
SOURCE_FILES = {
    "00-START-HERE.txt", "50-slovar-poley-raschet-metrami.docx",
    "51-algoritm-raschet-metrami.pdf", "52-chek-list-raschet-metrami.docx",
    "53-zapros-status-obekta.docx", "54-zapros-sostoyanie-escrow.docx",
    "55-pamyatka-punkt-ustupki-escrow.pdf", "56-pervyy-den-do-podpisi.docx",
}
TITLE = "Система проверки расчётов недвижимостью и уступки прав"
FORBIDDEN = r"шаблон|юридическ\w*\s+консультац|не\s+заменяет\s+юрист|не\s+гарантия\s+взыскания|колонк[а-яё]*|светло[- ‐‑–]?золотист[а-яё]*|Остальное считается само|Значения подставляются сами"


def checks(text):
    flat = " ".join(text.split())
    refs = set(re.findall(r"\b\d{2}-[A-Za-z0-9-]+\.(?:txt|docx|pdf|xlsx)\b", text))
    return {
        "plain_utf8_no_bom_or_control": not text.startswith("\ufeff") and not any(ord(c) < 32 and c != "\n" for c in text),
        "subject_present": text.startswith("Тема: "),
        "approved_product_name": TITLE in flat,
        "all_eight_references_match_frozen_nomination": refs == SOURCE_FILES,
        "urgent_first_day_route": "Начните с 56-pervyy-den-do-podpisi.docx" in flat,
        "escrow_step_two": "На шаге 2 алгоритма используйте 54-zapros-sostoyanie-escrow.docx" in flat,
        "status_step_three": "На шаге 3 алгоритма используйте 53-zapros-status-obekta.docx" in flat,
        "verified_support_contact": "marzhavbetone@yandex.ru" in text and "номер заказа" in flat,
        "no_forbidden_editorial_terms": re.search(FORBIDDEN, flat, re.I) is None,
        "no_unresolved_placeholders": re.search(r"\{\{|\}\}|\[\[|TODO|TBD|<[^>]+>", text, re.I) is None,
        "no_price": re.search(r"[₽$]|\b\d[\d ]+\s*(?:руб|RUB)", text, re.I) is None,
        "no_invented_download_url": re.search(r"https?://", text, re.I) is None,
        "no_internal_release_labels": re.search(r"G1.?G8|HOLD|SHA-?256|\bP11\b|\bT6\b|\bPR\s*#", text, re.I) is None,
        "value_and_support": "маржу по объекту" in flat and "«Маржа в бетоне»" in text,
        "readable_lines_final_newline": text.endswith("\n") and max(map(len, text.splitlines()), default=0) <= 88,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    data = (args.root / LETTER).read_bytes()
    text = data.decode("utf-8", errors="strict")
    positive = checks(text)
    mutations = {
        "nonexistent_reference": (text.replace("54-zapros-sostoyanie-escrow.docx", "54-missing.docx"), "all_eight_references_match_frozen_nomination"),
        "missing_support": (text.replace("marzhavbetone@yandex.ru", ""), "verified_support_contact"),
        "forbidden_word": (text + "Типовой шаблон.\n", "no_forbidden_editorial_terms"),
        "unresolved_link_token": (text + "{{DOWNLOAD_URL}}\n", "no_unresolved_placeholders"),
        "wrong_step": (text.replace("На шаге 2 алгоритма", "На шаге 4 алгоритма"), "escrow_step_two"),
        "legacy_t6_reference": (text.replace("56-pervyy-den-do-podpisi.docx", "01-poryadok-dnya-kogda-prosyat-podpisat.docx"), "all_eight_references_match_frozen_nomination"),
    }
    negative = {name: not checks(changed)[gate] for name, (changed, gate) in mutations.items()}
    passed = all(positive.values()) and all(negative.values())
    result = {
        "verdict": "PASS_AUTHOR_LETTER_CONTRACT_ONLY" if passed else "FAIL",
        "source_contract": "PR625 frozen eight-file nomination; fields read through GitHub connector",
        "letter_sha256": hashlib.sha256(data).hexdigest(),
        "letter_git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
        "bytes": len(data), "lines": len(text.splitlines()),
        "positive_checks": positive, "negative_mutations_detected": negative,
        "independent_review": "PENDING", "release": "HOLD",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
