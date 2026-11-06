#!/usr/bin/env python3
"""Retired T2/T3 HTML and unpacked-folder regression; active orders remain strict.

Offline: no network, no payments, no production writes, no protected ZIP reads.
"""
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + ".py"))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_page_renewal(preview) -> int:
    mapping = {
        "t2-peredacha-ispolnitelnoy-dokumentacii.html": "p4-ispolnitelnaya-dokumentaciya-pto.html",
        "t3-odnostoronniy-akt-i-zachet.html": "p5-shtrafy-uderzhaniya.html",
    }
    sold = preview.catalog()
    assert "t2" not in sold and "t3" not in sold, "T2/T3 still sellable in source config"
    for filename, parent in mapping.items():
        path = ROOT / "products" / filename
        txt = path.read_text(encoding="utf-8")
        assert "noindex,follow" in txt, filename
        assert "add-to-cart" not in txt and 'data-sku="t' not in txt, filename
        assert "Снят с продажи" in txt and f'href="{parent}"' in txt, filename
        unchanged, error = preview.render(path, sold)
        assert unchanged == txt and error == "", f"{filename}: {error}"
        # A future buy CTA or a future catalog entry must re-enable the FAIL.
        with TemporaryDirectory(prefix="nsp-retired-preview-") as d:
            probe = Path(d) / filename
            probe.write_text(txt.replace("Снят с продажи", "Добавить в корзину add-to-cart", 1), encoding="utf-8")
            assert preview.render(probe, sold)[1], f"{filename}: buy CTA mutation accepted"
            sku = filename.split("-")[0]
            assert preview.render(probe, {**sold, sku: "active"})[1], filename
    return len(mapping)


def verify_missing_manifests(packages) -> int:
    with TemporaryDirectory(prefix="nsp-retired-packages-") as d:
        base = Path(d)
        store = base / "products-storage"
        pages = base / "pages"
        pages.mkdir()
        store.mkdir()
        active = store / "active"
        t2 = store / "14-peredacha-id-pod-podpis"
        t3 = store / "17-odnostoronniy-akt-i-zachet"
        for folder in (active, t2, t3):
            folder.mkdir()
        (active / "MANIFEST.md").write_text("## Состав\n", encoding="utf-8")
        # Two classes of broken historical storage: absent and stale MANIFEST.
        (t3 / "MANIFEST.md").write_text("## Состав\n- `not-present.docx`\n", encoding="utf-8")
        cases = [
            ({"p4": "active"}, 0, "retired folders"),
            ({"p4": "active", "t2": t2.name}, 1, "re-sold missing T2"),
            ({"p4": "active", "t3": t3.name}, 1, "re-sold stale T3"),
        ]
        with patch.object(packages, "STORAGE", store), patch.object(packages, "PAGES", pages):
            for dirs, status, label in cases:
                with patch.object(packages, "catalog", return_value=dirs):
                    output = io.StringIO()
                    with redirect_stdout(output):
                        result = packages.main()
                    assert result == status, f"{label} exit={result}: {output.getvalue()[-500:]}"
                    if status == 0:
                        assert "АРХИВ СНЯТОГО SKU" in output.getvalue(), label
            # An unaddressed but non-retired folder must NOT be waived.
            unexpected = store / "18-other-missing-manifest"
            unexpected.mkdir()
            with patch.object(packages, "catalog", return_value={"p4": "active"}):
                with redirect_stdout(io.StringIO()):
                    assert packages.main() == 1, "unknown archive exemption"
            unexpected.rmdir()
            # FREE files never qualify for an archived folder exception.
            free = store / "00-free-check"
            free.mkdir()
            with patch.object(packages, "catalog", return_value={"p4": "active"}):
                with redirect_stdout(io.StringIO()):
                    assert packages.main() == 1, "FREE exempted from validation"
    return len(cases) + 2


def main() -> None:
    packages = load("check_packages")
    preview = load("build_preview")
    pages = verify_page_renewal(preview)
    cases = verify_missing_manifests(packages)
    print(f"RETIRED_STOREFRONT_ARCHIVE_PASS pages={pages} scenarios={cases} "
          "no_active_manifest_waiver=1 checkout_routes=0")


if __name__ == "__main__":
    main()
