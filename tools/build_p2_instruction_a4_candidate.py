#!/usr/bin/env python3
"""Build a copy-only A4 candidate from the nominated P2 instruction DOCX."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

EXPECTED_SOURCE_SHA256 = "a27ffb94bb47a66743fe01d188055813159a04117d09514db8f8aeef9c14f609"
DOCUMENT_MEMBER = "word/document.xml"
SOURCE_PGSZ = b'<w:pgSz w:w="12240" w:h="15840"/>'
A4_PGSZ = b'<w:pgSz w:w="11906" w:h="16838"/>'
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def document_text_sequence(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    return [node.text or "" for node in root.iter(f"{{{W_NS}}}t")]


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def build_candidate(source: Path, output: Path) -> dict:
    actual_source_sha = sha256_file(source)
    if actual_source_sha != EXPECTED_SOURCE_SHA256:
        raise ValueError(
            f"source SHA256 mismatch: expected {EXPECTED_SOURCE_SHA256}, got {actual_source_sha}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    before_hashes: dict[str, str] = {}
    try:
        with zipfile.ZipFile(source, "r") as source_zip:
            infos = source_zip.infolist()
            names = [info.filename for info in infos]
            if names.count(DOCUMENT_MEMBER) != 1:
                raise ValueError(f"expected exactly one {DOCUMENT_MEMBER} member")
            source_document = source_zip.read(DOCUMENT_MEMBER)
            if source_document.count(SOURCE_PGSZ) != 1:
                raise ValueError("expected exactly one nominated Letter pgSz element")
            if A4_PGSZ in source_document:
                raise ValueError("source already contains target A4 pgSz element")
            candidate_document = source_document.replace(SOURCE_PGSZ, A4_PGSZ, 1)
            if candidate_document.count(A4_PGSZ) != 1:
                raise ValueError("candidate A4 pgSz verification failed")
            if candidate_document.replace(A4_PGSZ, SOURCE_PGSZ, 1) != source_document:
                raise ValueError("document.xml changed beyond the nominated pgSz replacement")
            if document_text_sequence(candidate_document) != document_text_sequence(source_document):
                raise ValueError("document text sequence changed")

            with zipfile.ZipFile(tmp_path, "w") as output_zip:
                for info in infos:
                    data = source_zip.read(info.filename)
                    before_hashes[info.filename] = sha256_bytes(data)
                    if info.filename == DOCUMENT_MEMBER:
                        data = candidate_document
                    output_zip.writestr(info, data)

        with tmp_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(tmp_path, output)
        dir_fd = os.open(output.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise

    with zipfile.ZipFile(output, "r") as candidate_zip:
        after_hashes = {
            info.filename: sha256_bytes(candidate_zip.read(info.filename))
            for info in candidate_zip.infolist()
        }
        candidate_document = candidate_zip.read(DOCUMENT_MEMBER)

    changed_members = sorted(
        name for name in before_hashes if before_hashes[name] != after_hashes.get(name)
    )
    if set(before_hashes) != set(after_hashes):
        raise ValueError("ZIP member set changed")
    if changed_members != [DOCUMENT_MEMBER]:
        raise ValueError(f"unexpected changed members: {changed_members}")
    if candidate_document.count(A4_PGSZ) != 1:
        raise ValueError("persisted candidate A4 pgSz verification failed")

    return {
        "status": "PASS_DETERMINISTIC_CANDIDATE_BUILD_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(source),
            "sha256": actual_source_sha,
            "bytes": source.stat().st_size,
        },
        "candidate": {
            "path": str(output),
            "sha256": sha256_file(output),
            "bytes": output.stat().st_size,
        },
        "changed_members": changed_members,
        "unchanged_member_count": len(before_hashes) - len(changed_members),
        "text_sequence_unchanged": True,
        "source_pgSz_twips": [12240, 15840],
        "candidate_pgSz_twips": [11906, 16838],
        "scope": "copy-only OOXML page-size candidate; no source replacement",
        "not_accepted": [
            "visual layout",
            "native Microsoft Word behavior",
            "content",
            "legal",
            "release",
            "publication",
            "delivery",
        ],
        "model_calls": 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_candidate(args.input, args.output)
    except BaseException as exc:
        report = {
            "status": "FAIL_NOT_VERIFIED",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "source": str(args.input),
            "candidate": str(args.output),
            "model_calls": 0,
        }
        atomic_write_json(args.report, report)
        raise
    atomic_write_json(args.report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
