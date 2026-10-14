#!/usr/bin/env python3
"""Deterministic P11/T6 exact-SHA brand evidence inventory.

Read-only over buyer/source files. Writes one JSON report selected by --output.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE_HEAD = "d961b9c7c95b45919ef96347e5a0d27f4d6f0fcc"
ROOT_REL = Path("tools/candidates/portfolio-owner-pdf-20261013")
BUYER_REL = ROOT_REL / "13-raschet-metrami"
EXPECTED = {
    "00-START-HERE.txt": "2f895a2f2b8ea5e166c8f18dd416465f2651b3562068551fc9f26841fd5dcf3a",
    "50-slovar-poley-raschet-metrami.docx": "b0bd9d309115377c0e80c418d2dda1acdf3d33d4863feb2f15de69b70099427c",
    "51-algoritm-raschet-metrami.pdf": "2a4c98dc4a1b131dbccb787276f487a17a76a0c6643932c0ee0ca666601135d7",
    "52-chek-list-raschet-metrami.docx": "6094a91af0a2e750a1ef71f9b394ea49207af11f8c5420ade1a7da48ff79fd38",
    "53-zapros-status-obekta.docx": "c3fccbdc5e7e6841ca8c48b5ab1c199bdebe0d2f4990c232040d20f70bfc023e",
    "54-zapros-sostoyanie-escrow.docx": "8e76f513b4f72c51bd8e9ad1bd56c27409285585b2f38f96c76b5f8dfbfa4f96",
    "55-pamyatka-punkt-ustupki-escrow.pdf": "20f65a850db70836b2897dc747ed6478781641e3a4f5a537b094a7afec0814a2",
    "56-pervyy-den-do-podpisi.docx": "9c40a96498037b53a68ecea6f3ee57129a9f2c236d1073d1818c603016260807",
}
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
FALSE_VALUES = {"0", "false", "off", "no"}
BLUE_FAMILY = {"0000FF", "0563C1", "1F4D78", "1F4E78", "2E74B5", "2F5496", "4472C4", "5B9BD5"}
GRAPHITE_FAMILY = {"000000", "262626", "303438", "313539", "323539", "333333", "3F3F3F", "404040", "4A4A4A", "595959", "666666"}
GOLD_FAMILY = {"B08D57", "B89B5E", "C4A35A", "C7A85B", "C9A227", "D0B36C", "D6B85A"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


def active_bool(el: ET.Element) -> bool:
    return str(el.attrib.get(W + "val", "1")).lower() not in FALSE_VALUES


def counter_dict(c: collections.Counter) -> dict[str, int]:
    return dict(sorted(c.items(), key=lambda item: (-item[1], item[0])))


def _part_metrics(root: ET.Element) -> dict:
    colors: collections.Counter[str] = collections.Counter()
    fills: collections.Counter[str] = collections.Counter()
    fonts: collections.Counter[str] = collections.Counter()
    styles: collections.Counter[str] = collections.Counter()
    active_italic = 0
    inactive_italic = 0
    for el in root.findall(".//" + W + "i"):
        if active_bool(el):
            active_italic += 1
        else:
            inactive_italic += 1
    for el in root.findall(".//" + W + "color"):
        val = el.attrib.get(W + "val")
        if val and val.lower() != "auto":
            colors[val.upper()] += 1
    for el in root.findall(".//" + W + "shd"):
        val = el.attrib.get(W + "fill")
        if val and val.lower() != "auto":
            fills[val.upper()] += 1
    for el in root.findall(".//" + W + "rFonts"):
        for value in el.attrib.values():
            if value:
                fonts[str(value)] += 1
    for el in root.findall(".//" + W + "pStyle"):
        val = el.attrib.get(W + "val")
        if val:
            styles[val] += 1
    return {
        "paragraph_elements": len(root.findall(".//" + W + "p")),
        "table_elements": len(root.findall(".//" + W + "tbl")),
        "drawing_elements": len(root.findall(".//" + W + "drawing")),
        "active_italic_elements": active_italic,
        "inactive_italic_elements": inactive_italic,
        "explicit_text_colors": counter_dict(colors),
        "explicit_shading_fills": counter_dict(fills),
        "fonts": counter_dict(fonts),
        "paragraph_styles": counter_dict(styles),
    }


def _palette_facts(metrics: dict) -> dict:
    used = set(metrics["explicit_text_colors"]) | set(metrics["explicit_shading_fills"])
    return {
        "graphite_family_present": bool(used & GRAPHITE_FAMILY),
        "gold_family_present": bool(used & GOLD_FAMILY),
        "blue_family_present": bool(used & BLUE_FAMILY),
        "matched_graphite": sorted(used & GRAPHITE_FAMILY),
        "matched_gold": sorted(used & GOLD_FAMILY),
        "matched_blue": sorted(used & BLUE_FAMILY),
        "scope": "explicit values in document body, headers and footers only; no rendered-area inference",
    }


def docx_metrics(path: Path) -> dict:
    body_roots: list[ET.Element] = []
    style_roots: list[ET.Element] = []
    page_sizes: list[dict[str, str]] = []
    theme: dict[str, str] = {}
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        names = set(z.namelist())
        body_names = sorted(
            name for name in names
            if name == "word/document.xml"
            or (name.startswith("word/header") and name.endswith(".xml"))
            or (name.startswith("word/footer") and name.endswith(".xml"))
        )
        for name in body_names:
            root = ET.fromstring(z.read(name))
            body_roots.append(root)
            for el in root.findall(".//" + W + "pgSz"):
                page_sizes.append({
                    "w_twips": el.attrib.get(W + "w", ""),
                    "h_twips": el.attrib.get(W + "h", ""),
                    "orient": el.attrib.get(W + "orient", "portrait"),
                })
        if "word/styles.xml" in names:
            style_roots.append(ET.fromstring(z.read("word/styles.xml")))
        theme_names = sorted(name for name in names if name.startswith("word/theme/") and name.endswith(".xml"))
        for theme_name in theme_names:
            tr = ET.fromstring(z.read(theme_name))
            for key in ("dk1", "lt1", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6"):
                node = tr.find(".//" + A + key)
                if node is not None and len(node):
                    child = list(node)[0]
                    value = child.attrib.get("val") or child.attrib.get("lastClr")
                    if value:
                        theme[key] = value.upper()
    def merged(roots: list[ET.Element]) -> dict:
        total = {
            "paragraph_elements": 0, "table_elements": 0, "drawing_elements": 0,
            "active_italic_elements": 0, "inactive_italic_elements": 0,
        }
        colors: collections.Counter[str] = collections.Counter()
        fills: collections.Counter[str] = collections.Counter()
        fonts: collections.Counter[str] = collections.Counter()
        styles: collections.Counter[str] = collections.Counter()
        for root in roots:
            item = _part_metrics(root)
            for key in total:
                total[key] += item[key]
            colors.update(item["explicit_text_colors"])
            fills.update(item["explicit_shading_fills"])
            fonts.update(item["fonts"])
            styles.update(item["paragraph_styles"])
        total["explicit_text_colors"] = counter_dict(colors)
        total["explicit_shading_fills"] = counter_dict(fills)
        total["fonts"] = counter_dict(fonts)
        total["paragraph_styles"] = counter_dict(styles)
        return total
    body = merged(body_roots)
    styles = merged(style_roots)
    return {
        "zip_crc": "PASS" if bad is None else f"FAIL:{bad}",
        "document_body_headers_footers": body,
        "style_definitions": styles,
        "theme_colors": theme,
        "page_sizes": page_sizes,
        "body_palette_presence_facts": _palette_facts(body),
        "interpretation_guard": "style_definitions and theme_colors are not evidence that a format is rendered on a buyer-visible page",
    }


def pdf_metrics(path: Path) -> dict:
    info = cmd("pdfinfo", str(path))
    fonts = cmd("pdffonts", str(path))
    values: dict[str, str] = {}
    for line in info.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    font_rows = []
    for line in fonts.splitlines()[2:]:
        if line.strip():
            font_rows.append(re.split(r"\s{2,}", line.strip())[0])
    return {
        "pages": int(values.get("Pages", "0")),
        "page_size": values.get("Page size", ""),
        "pdf_version": values.get("PDF version", ""),
        "font_names": sorted(set(font_rows)),
    }


def json_load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_entry(repo: Path, root: Path, name: str) -> dict:
    expected = EXPECTED[name]
    if name == "00-START-HERE.txt":
        return {"status": "NOT_APPLICABLE_TEXT_ONLY", "pages": 0, "exact_input_sha_bound": True, "routes": []}
    if name.startswith("50-"):
        d = root / "p11-50-buyer-wording-native-20261014"
        receipt = json_load(d / "native-receipt.json")
        outputs = [d / "native/50.pdf", d / "native/50-1.png", d / "native/50-2.png"]
        return {
            "status": "EXACT_SHA_NATIVE_PDF_AND_PNG_PRESENT",
            "pages": 2,
            "exact_input_sha_bound": receipt["input"][name] == expected,
            "routes": [str((d / "native-receipt.json").relative_to(repo))] + [str(p.relative_to(repo)) for p in outputs],
            "output_sha256": {p.name: sha256(p) for p in outputs},
        }
    if name.startswith("53-"):
        d = root / "p11-50-53-ics-cleanup-20261014"
        receipt = json_load(d / "native-receipt.json")
        outputs = [d / "native/53.pdf", d / "native/53-1.png", d / "native/53-2.png", d / "native/53-3.png"]
        return {
            "status": "EXACT_SHA_NATIVE_PDF_AND_PNG_PRESENT",
            "pages": 3,
            "exact_input_sha_bound": receipt["inputs"][name] == expected,
            "routes": [str((d / "native-receipt.json").relative_to(repo))] + [str(p.relative_to(repo)) for p in outputs],
            "output_sha256": {p.name: sha256(p) for p in outputs},
        }
    if name.startswith("56-"):
        d = root / "p11-t6-dayone-20261014"
        job = ET.fromstring((d / "native/job-v2.xml").read_bytes())
        bound = job.find("file").attrib["sha256"] == expected
        outputs = [d / "native/output-v2.pdf", d / "native/final-1.png"]
        return {
            "status": "EXACT_SHA_NATIVE_PDF_AND_PNG_PRESENT",
            "pages": 1,
            "exact_input_sha_bound": bound,
            "routes": [str((d / "native/job-v2.xml").relative_to(repo)), str((d / "native/report-v2.xml").relative_to(repo))] + [str(p.relative_to(repo)) for p in outputs],
            "output_sha256": {p.name: sha256(p) for p in outputs},
        }
    delta = json_load(root / "p11-buyer-fixes-20261014/delta-acceptance.json")
    bound = delta["buyer_files"][name] == expected
    if name.startswith("51-") or name.startswith("55-"):
        p = root / "p11-buyer-fixes-20261014/evidence/51-55-report.xml"
        report = ET.fromstring(p.read_bytes())
        tag = name[:2]
        row = next(el for el in report.findall("file") if el.attrib["tag"] == tag)
        return {
            "status": "EXACT_BUYER_PDF_IS_NATIVE_OUTPUT",
            "pages": pdf_metrics(root / "13-raschet-metrami" / name)["pages"],
            "exact_input_sha_bound": bound and row.attrib["pdf_sha256"] == expected,
            "routes": [str(p.relative_to(repo)), str((root / "13-raschet-metrami" / name).relative_to(repo))],
            "output_sha256": {name: expected},
        }
    if name.startswith("52-"):
        pdf = root / "p11-buyer-fixes-20261014/evidence/52-native.pdf"
        report_path = root / "p11-buyer-fixes-20261014/evidence/52-report.xml"
    elif name.startswith("54-"):
        pdf = root / "p11-buyer-fixes-20261014/evidence/54-native.pdf"
        report_path = root / "p11-buyer-fixes-20261014/evidence/54-report.xml"
    else:
        raise AssertionError(name)
    report = ET.fromstring(report_path.read_bytes())
    tag = name[:2] if name.startswith("54-") else "f52"
    row = next(el for el in report.findall("file") if el.attrib["tag"] == tag)
    pdf_sha = sha256(pdf)
    return {
        "status": "EXACT_SHA_NATIVE_PDF_PRESENT",
        "pages": pdf_metrics(pdf)["pages"],
        "exact_input_sha_bound": bound and row.attrib["pdf_sha256"] == pdf_sha,
        "routes": [str((root / "p11-buyer-fixes-20261014/delta-acceptance.json").relative_to(repo)), str(report_path.relative_to(repo)), str(pdf.relative_to(repo))],
        "output_sha256": {pdf.name: pdf_sha},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    repo = args.root.resolve()
    head = cmd("git", "-C", str(repo), "rev-parse", "HEAD").strip()
    if head != BASE_HEAD:
        raise SystemExit(f"wrong head: {head}")
    root = repo / ROOT_REL
    files = []
    total_pages = 0
    for name, expected in EXPECTED.items():
        path = root / "13-raschet-metrami" / name
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"sha mismatch {name}: {actual}")
        evidence = evidence_entry(repo, root, name)
        if not evidence["exact_input_sha_bound"]:
            raise SystemExit(f"evidence not exact-SHA bound: {name}")
        total_pages += evidence["pages"]
        static = docx_metrics(path) if path.suffix == ".docx" else pdf_metrics(path) if path.suffix == ".pdf" else {
            "bytes": path.stat().st_size,
            "lines": len(path.read_text(encoding="utf-8").splitlines()),
        }
        files.append({
            "name": name,
            "path": str(path.relative_to(repo)),
            "sha256": actual,
            "bytes": path.stat().st_size,
            "format": path.suffix.lstrip(".").upper() or "TEXT",
            "static_facts": static,
            "visual_evidence": evidence,
        })
    missing = [row["name"] for row in files if row["visual_evidence"]["status"].startswith("MISSING")]
    report = {
        "schema_version": 1,
        "id": "P11-T6-BRAND-PORTFOLIO-INVENTORY-20261014",
        "source_head": head,
        "scope": "READ_ONLY_EXACT_SHA_BRAND_EVIDENCE_INVENTORY_ONLY",
        "accepted_archive_sha256": "6a07f3c81152a22c3f2a8f127862e8a4e1ea6cafd0f750095d1933a5c095f572",
        "files_checked": len(files),
        "files": files,
        "summary": {
            "identity": "PASS_8_OF_8_EXACT_SHA",
            "visual_evidence_pages": total_pages,
            "expected_visual_pages": 17,
            "page_evidence_coverage": "PASS_17_OF_17" if total_pages == 17 else "FAIL",
            "missing_exact_sha_render_files": missing,
            "brand_static_scope": "OOXML_COLOR_FONT_STYLE_FACTS_PLUS_PDF_METADATA",
            "brand_visual_acceptance": "NOT_CLAIMED_BY_AUTHOR_INVENTORY",
            "source_files_changed": 0,
            "model_calls": 0,
            "paid_api_calls": 0,
            "release": "HOLD",
            "G1_G8": "0/13",
        },
        "limitations": [
            "Exact native/PDF evidence presence does not itself prove independent brand conformance.",
            "OOXML style/theme definitions do not prove rendered body formatting; they are reported separately from document/header/footer facts.",
            "PDF metadata and fonts do not establish page colour proportions; page images/PDFs remain the visual source.",
            "This report does not accept legal content, controlled delivery, canonical replacement, release, publication, prices, SKU, payment or live delivery.",
        ],
        "next_step": "Independent visual review of all 17 exact-SHA pages using the mapped evidence; no new Office render is needed unless the reviewer proves an evidence mismatch.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(args.output)
    print(json.dumps({
        "status": "PASS_INVENTORY_AUTHOR_SCOPE_ONLY",
        "report": str(args.output),
        "report_sha256": sha256(args.output),
        "files": len(files),
        "visual_pages": total_pages,
        "missing": missing,
        "model_calls": 0,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
