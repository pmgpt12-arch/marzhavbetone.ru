#!/usr/bin/env python3
"""Build an exact-source P11 release/rollback candidate without touching runtime."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

BASE = "03ebb0f1970a295d69fc6e8bc175d9e1d5191f76"
BINDING_DIR = Path("tools/candidates/p11-isolated-delivery-binding-20261014")
BINDING_BUILDER_SHA256 = "e71b35efc4c296f1c90c91f41bf5320cc6cf6606f8503dc39b0bdfc9a4a7b800"
BINDING_HELPERS_SHA256 = "22988c10c51a769110a9cfdbfdff8955e7a99e987eb3ea30721616f71e9b5fa8"
EXPECTED_BLOBS = {
    "products-config.php": "1d2a0225c3974d0fd44b9011b1b06803ceadb16e",
    "download.php": "f642cf899acf0915e27ced6f626bdc78424c41c9",
    "payment.php": "917edd032f203563dafff86d553c3863925082f1",
}
ACCEPTED_BINDING_OUTPUT_SHA256 = {
    "download.php": "2ccd9b2507cfc7e64eeada608825f507b4c780cd898c4cdc799cdce67691c92d",
}
OLD_PAYMENT_BLOCK = """// Издание P1 фиксируется до заказа и обращения к кассе.
// Клиентское поле edition не используется: снимок создаёт сервер.
foreach ($validatedItems as &$position) {
    if ($position['sku'] !== 'p1') continue;
    $edition = mvb_capture_p1_edition();
    if ($edition === null) {
        http_response_code(503);
        echo json_encode(['ok' => false, 'message' => 'Комплект временно недоступен. Повторите заказ позднее.'], JSON_UNESCAPED_UNICODE);
        exit;
    }
    $position['edition'] = $edition;
}
"""
NEW_PAYMENT_BLOCK = """// Издание P1/P11 фиксирует только сервер до записи заказа и обращения к кассе.
// Клиентское поле edition отбрасывается при построении $validatedItems.
foreach ($validatedItems as &$position) {
    if ($position['sku'] === 'p1') {
        $edition = mvb_capture_p1_edition();
    } elseif ($position['sku'] === 'p11') {
        $edition = mvb_p11_binding_edition();
        if (mvb_p11_stage_edition($edition) === null) $edition = null;
    } else {
        continue;
    }
    if ($edition === null) {
        http_response_code(503);
        echo json_encode(['ok' => false, 'message' => 'Комплект временно недоступен. Повторите заказ позднее.'], JSON_UNESCAPED_UNICODE);
        exit;
    }
    $position['edition'] = $edition;
}
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def replace_once(text: str, before: str, after: str) -> str:
    if text.count(before) != 1:
        raise ValueError("Exact unique payment anchor failed")
    return text.replace(before, after, 1)


def load_binding_builder(repo: Path):
    builder_path = repo / BINDING_DIR / "build_candidate.py"
    helper_path = Path(__file__).resolve().parent / "binding_helpers.php.txt"
    if sha256(builder_path.read_bytes()) != BINDING_BUILDER_SHA256:
        raise ValueError("Accepted binding builder drift")
    if sha256(helper_path.read_bytes()) != BINDING_HELPERS_SHA256:
        raise ValueError("Accepted binding helpers drift")
    spec = importlib.util.spec_from_file_location("accepted_p11_binding_builder", builder_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load accepted binding builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, helper_path.read_text()


def build(repo: Path, inputs: dict[str, bytes]):
    for name, expected in EXPECTED_BLOBS.items():
        if git_blob(inputs[name]) != expected:
            raise ValueError("Source drift: " + name)
    binding, helpers = load_binding_builder(repo)
    bound, _ = binding.build(
        {"products-config.php": inputs["products-config.php"], "download.php": inputs["download.php"]},
        helpers,
    )
    for name, expected in ACCEPTED_BINDING_OUTPUT_SHA256.items():
        if sha256(bound[name]) != expected:
            raise ValueError("Accepted binding output drift: " + name)
    payment = replace_once(inputs["payment.php"].decode(), OLD_PAYMENT_BLOCK, NEW_PAYMENT_BLOCK).encode()
    outputs = {
        "products-config.php": bound["products-config.php"],
        "download.php": bound["download.php"],
        "payment.php": payment,
    }
    release_patch = "".join(
        "".join(difflib.unified_diff(
            inputs[name].decode().splitlines(True),
            outputs[name].decode().splitlines(True),
            fromfile="a/" + name,
            tofile="b/" + name,
            n=0,
        ))
        for name in outputs
    )
    rollback_patch = "".join(
        "".join(difflib.unified_diff(
            outputs[name].decode().splitlines(True),
            inputs[name].decode().splitlines(True),
            fromfile="a/" + name,
            tofile="b/" + name,
            n=0,
        ))
        for name in outputs
    )
    return outputs, release_patch.encode(), rollback_patch.encode()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    read = lambda name: subprocess.check_output(
        ["git", "-C", str(args.repo), "show", BASE + ":" + name], timeout=15
    )
    inputs = {name: read(name) for name in EXPECTED_BLOBS}
    outputs, release_patch, rollback_patch = build(args.repo, inputs)
    manifest = {
        "schema_version": 1,
        "id": "P11-ROLLBACK-ENTITLEMENT-REMEDIATION-20261014",
        "status": "BUILT_NOT_ACCEPTED",
        "base": BASE,
        "input_blobs": EXPECTED_BLOBS,
        "input_sha256": {name: sha256(data) for name, data in inputs.items()},
        "output_sha256": {name: sha256(data) for name, data in outputs.items()},
        "accepted_binding_output_sha256": ACCEPTED_BINDING_OUTPUT_SHA256,
        "release_patch_sha256": sha256(release_patch),
        "rollback_patch_sha256": sha256(rollback_patch),
        "runtime_paths": list(outputs),
        "model_calls": 0,
        "live_changes": False,
    }
    atomic_write(args.output_dir / "release-candidate.patch", release_patch)
    atomic_write(args.output_dir / "rollback-candidate.patch", rollback_patch)
    atomic_write(
        args.output_dir / "build-manifest.json",
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode(),
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
