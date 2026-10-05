"""Настоящий mvb_build_product_zip('p2'): состав и sha256 каждого члена против
базы b0d91bb (git show)."""
import hashlib
import subprocess
import tempfile
import zipfile
from pathlib import Path

WT = Path("/home/denis/projects/marzhavbetone.ru/.worktrees/codex-correction-388-20261005")
BASE = "b0d91bba404064125e453e5b498c95defc1c7492"
CHANGED = {"00-INSTRUKCIYA.docx", "00-INSTRUKCIYA.pdf", "03-uvedomlenie-o-doprabotah.docx"}
with tempfile.TemporaryDirectory() as tmp:
    orders = Path(tmp) / "orders"
    orders.mkdir()
    code = (f"define('ORDERS_DIR', {str(orders)!r});"
            f"define('PRODUCTS_DIR', {str(WT / 'products-storage')!r});"
            f"require {str(WT / 'products-config.php')!r};"
            "echo (string)mvb_build_product_zip('p2');")
    r = subprocess.run(["php", "-r", code], capture_output=True, text=True, check=True)
    with zipfile.ZipFile(r.stdout.strip()) as z:
        names = sorted(z.namelist())
        print("members", len(names), "testzip", z.testzip())
        bad = []
        for n in names:
            new = hashlib.sha256(z.read(n)).hexdigest()
            old = hashlib.sha256(subprocess.run(
                ["git", "-C", str(WT), "show", f"{BASE}:products-storage/02-dopraboty-bez-poter/{n}"],
                capture_output=True, check=True).stdout).hexdigest()
            state = "changed" if new != old else "same"
            if (state == "changed") != (n in CHANGED):
                bad.append(n)
            print(f"{state:8} {new[:12]} (base {old[:12]}) {n}")
        print("unexpected:", bad or "none")
