#!/usr/bin/env python3
"""Capture an evidence package for the accepted 88-page static snapshot.

This is deliberately a render-only gate. It neither exercises nor accepts the
ten dynamic endpoints named by the source snapshot, and it never mutates page
sources. A failure still leaves an atomic partial report and receipt.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse
try:
    from tools.browser_isolation import handle_external
except ModuleNotFoundError:
    from browser_isolation import handle_external

EXPECTED_REPORT_SHA256 = "029e2d0763775a05afd8f6fa86c01a6c9fe94af67e597602e4b3779edfaeecbb"
EXPECTED_PAGE_COUNT = 88
VIEWPORTS = {
    "mobile-390x844": {"width": 390, "height": 844},
    "desktop-1440x900": {"width": 1440, "height": 900},
}
OVERFLOW_TOLERANCE_PX = 1

P3_PRICE_PAGE = "products/p3-shablony-ks2-ks3.html"
P3_APPROVED_TITLE = "Комплект «КС-2 без возврата»: шаблоны, реестры, алгоритм — 17 900 ₽"


def accepted_title_match(source_page: dict, observed_title: str) -> bool:
    """A changed title is accepted only for the exact SHA-pinned P3 price change."""
    if observed_title == source_page["title"]:
        return True
    if source_page.get("source_path") != P3_PRICE_PAGE or observed_title != P3_APPROVED_TITLE:
        return False
    try:
        from tools.check_p3_current_site_delta import validate_current_p3_delta
    except ModuleNotFoundError:
        from check_p3_current_site_delta import validate_current_p3_delta
    validate_current_p3_delta()
    return True


def staging_render_source(source: dict, root: Path) -> dict:
    """Project render expectations from the pinned staging source; keep history intact."""
    try:
        from tools import check_p3_current_site_delta as gate
        from tools.build_static_content_snapshot import analyze_html, attributes
    except ModuleNotFoundError:
        import check_p3_current_site_delta as gate
        from build_static_content_snapshot import analyze_html, attributes
    if root.resolve() != gate.ROOT.resolve():
        raise ValueError("staging render scope requires this repository root")
    scope = gate.validate_current_customer_route_delta()
    projected = copy.deepcopy(source)
    paths = {page['source_path'] for page in projected['pages']}
    blobs = {}
    def pinned(path):
        if path not in blobs:
            blobs[path] = gate.git('show', scope['source_ref'] + ':' + path)
        return blobs[path]
    for page in projected['pages']:
        path = page['source_path']
        raw = pinned(path)
        html = raw.decode('utf-8')
        render_path = path
        page['expected_final_route'] = page['public_route']
        for tag in re.findall(r'<meta\b[^>]*>', html, re.I):
            attrs = attributes(tag)
            if attrs.get('http-equiv', '').lower() != 'refresh':
                continue
            redirect = re.fullmatch(r'0\s*;\s*url=(/[^?#]+)', attrs.get('content', ''), re.I)
            if not redirect or redirect.group(1).lstrip('/') not in paths:
                raise ValueError('staging redirect must target a pinned static page')
            page['expected_final_route'] = redirect.group(1)
            render_path = redirect.group(1).lstrip('/')
        render_raw = pinned(render_path)
        info = analyze_html(render_path, render_raw.decode('utf-8'))
        page['historical_source_sha256'] = page.get('source_sha256')
        page['source_ref'] = scope['source_ref']
        page['source_sha256'] = sha256_bytes(raw)
        page['source_bytes'] = len(raw)
        page['source_blob'] = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        page['render_source_path'] = render_path
        page['render_source_sha256'] = sha256_bytes(render_raw)
        for key in ('title', 'h1', 'canonical'):
            page[key] = info[key]
    projected.setdefault('lineage', {})['render_staging_scope'] = scope
    return projected




def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def validate_source_report(raw: bytes, expected_sha: str = EXPECTED_REPORT_SHA256) -> dict:
    actual_sha = sha256_bytes(raw)
    if actual_sha != expected_sha:
        raise ValueError(f"source report SHA256 {actual_sha}, expected {expected_sha}")
    data = json.loads(raw)
    if data.get("status") != "PASS_STATIC_SOURCE_SNAPSHOT_ONLY":
        raise ValueError("source report does not carry the accepted static-only status")
    pages = data.get("pages")
    if not isinstance(pages, list) or len(pages) != EXPECTED_PAGE_COUNT:
        raise ValueError(f"source report has {len(pages) if isinstance(pages, list) else 'invalid'} pages")
    if data.get("counts", {}).get("static_pages") != EXPECTED_PAGE_COUNT:
        raise ValueError("source report count disagrees with its pages")
    routes = [page.get("public_route") for page in pages]
    source_paths = [page.get("source_path") for page in pages]
    if any(not isinstance(route, str) or not route.startswith("/") for route in routes):
        raise ValueError("source report contains an invalid public route")
    if len(routes) != len(set(routes)) or len(source_paths) != len(set(source_paths)):
        raise ValueError("source report contains duplicate routes or source paths")
    if data.get("acceptance_limits", {}).get("browser_render_accepted") is not False:
        raise ValueError("source report no longer declares browser render as open")
    if len(data.get("excluded_dynamic_endpoints", [])) != 10:
        raise ValueError("dynamic endpoint exclusion contract changed")
    return data


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(port: int, process: subprocess.Popen, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"PHP server exited early with {process.returncode}")
        with contextlib.closing(socket.socket()) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError("PHP server did not become ready within 10 seconds")


def normalized_text(value: str) -> str:
    return " ".join(value.split())


def canonical_value(page) -> str | None:
    return page.evaluate("""() => {
      const node = document.querySelector('link[rel~="canonical"]');
      return node ? node.href : null;
    }""")


def dynamic_disposition(path: str, excluded: set[str]) -> str:
    if path not in excluded:
        return "not_dynamic"
    if path == "/app-script.php":
        return "allowed_render_dependency_not_accepted"
    return "inert_204_stub_not_executed"


def make_dynamic_route_handler(excluded: set[str], observed: list[dict], origin=None, external=None):
    def handler(route_object, request) -> None:
        if origin and handle_external(route_object, request, origin, external):
            return
        parsed = urlparse(request.url)
        disposition = dynamic_disposition(parsed.path, excluded)
        if disposition == "not_dynamic":
            route_object.continue_()
            return
        observed.append({
            "path": parsed.path,
            "method": request.method,
            "disposition": disposition,
        })
        if disposition == "allowed_render_dependency_not_accepted":
            route_object.continue_()
            return
        route_object.fulfill(status=204, body="", content_type="text/plain")

    return handler


def materialize_lazy_images(page, settle_timeout_ms: int = 2500) -> dict:
    """Bring every native lazy image into view and verify it resolved.

    Playwright's full-page screenshot expands the capture surface but does not
    itself guarantee that native ``loading=lazy`` images ever enter the
    viewport.  Visit each image in document order, wait for load/error with a
    bounded timeout, then restore the first fold before collecting metrics and
    the screenshot.
    """
    lazy_images = page.locator('img[loading="lazy"]')
    count = lazy_images.count()
    hidden = 0
    for index in range(count):
        image = lazy_images.nth(index)
        if not image.is_visible():
            hidden += 1
            continue
        image.scroll_into_view_if_needed(timeout=settle_timeout_ms)
        image.evaluate(
            """(img, timeoutMs) => new Promise((resolve) => {
              const done = () => resolve();
              if (img.complete) { done(); return; }
              img.addEventListener('load', done, {once: true});
              img.addEventListener('error', done, {once: true});
              setTimeout(done, timeoutMs);
            })""",
            settle_timeout_ms,
        )
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(250)
    states = page.locator('img[loading="lazy"]').evaluate_all(
        """images => images.map(img => ({
          src: img.currentSrc || img.src || '',
          complete: img.complete,
          naturalWidth: img.naturalWidth,
          visible: !!(img.getClientRects().length &&
            getComputedStyle(img).visibility !== 'hidden' &&
            getComputedStyle(img).display !== 'none')
        }))"""
    )
    visible = [item for item in states if item["visible"]]
    unresolved = [item for item in visible if not item["complete"] or item["naturalWidth"] <= 0]
    return {
        "count": len(states),
        "visible": len(visible),
        "hidden": hidden,
        "materialized": len(visible) - len(unresolved),
        "unresolved": unresolved,
    }


def make_contact_sheets(output: Path, manifest: list[dict]) -> list[dict]:
    from PIL import Image, ImageDraw, ImageOps

    results = []
    for viewport in VIEWPORTS:
        rows = [item for item in manifest if item["viewport"] == viewport]
        for sheet_kind in ("first-fold", "full-page"):
            for part, offset in enumerate(range(0, len(rows), 44), start=1):
                chunk = rows[offset:offset + 44]
                columns, tile_w, tile_h, label_h = 4, 320, 180, 38
                row_count = (len(chunk) + columns - 1) // columns
                sheet = Image.new("RGB", (columns * tile_w, row_count * (tile_h + label_h)), "white")
                draw = ImageDraw.Draw(sheet)
                for index, item in enumerate(chunk):
                    image_path = output / item["relative_path"]
                    with Image.open(image_path) as source:
                        rendered = source.convert("RGB")
                        if sheet_kind == "first-fold":
                            fold_height = min(rendered.height, VIEWPORTS[viewport]["height"])
                            rendered = rendered.crop((0, 0, rendered.width, fold_height))
                        thumb = ImageOps.contain(rendered, (tile_w - 8, tile_h - 8))
                    x = (index % columns) * tile_w
                    y = (index // columns) * (tile_h + label_h)
                    sheet.paste(thumb, (x + 4, y + 4))
                    label = item["public_route"]
                    if len(label) > 48:
                        label = label[:45] + "..."
                    draw.text((x + 5, y + tile_h + 4), label, fill="black")
                    draw.text((x + 5, y + tile_h + 20), item["sha256"][:16], fill="#555555")
                relative = Path("contact-sheets") / f"{sheet_kind}-{viewport}-part-{part}.jpg"
                destination = output / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                sheet.save(destination, format="JPEG", quality=86, optimize=True)
                results.append({
                    "kind": sheet_kind,
                    "viewport": viewport,
                    "part": part,
                    "pages": len(chunk),
                    "relative_path": relative.as_posix(),
                    "sha256": sha256_file(destination),
                    "bytes": destination.stat().st_size,
                })
    return results


def capture(root: Path, report_path: Path, output: Path, staging_source: bool = False,
            browser_executable: str | None = None) -> tuple[dict, int]:
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    output.mkdir(parents=True, exist_ok=True)
    raw = b""
    source = None
    log_path = output / "php-server.log"
    port = None
    server = None
    browser = None
    manifest: list[dict] = []
    failures: list[dict] = []
    dynamic_requests_observed: list[dict] = []
    external_requests_observed: list[dict] = []
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_ref": os.getenv("GITHUB_REF"),
        "github_head_ref": os.getenv("GITHUB_HEAD_REF"),
        "evidence_head_sha": os.getenv("EVIDENCE_HEAD_SHA"),
    }
    status = "FAIL_BROWSER_RENDER_SNAPSHOT"
    fatal_error = None
    try:
        raw = report_path.read_bytes()
        source = validate_source_report(raw)
        if staging_source:
            source = staging_render_source(source, root)
            environment['staging_source_scope'] = source['lineage']['render_staging_scope']
        port = free_port()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("playwright is required") from exc

        log_stream = log_path.open("wb")
        server = subprocess.Popen(
            ["php", "-S", f"127.0.0.1:{port}", "-t", str(root)],
            cwd=root,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
        )
        wait_for_server(port, server)
        base = f"http://127.0.0.1:{port}"
        excluded = {"/" + item.lstrip("/") for item in source["excluded_dynamic_endpoints"]}

        with sync_playwright() as playwright:
            environment["playwright"] = getattr(sys.modules.get("playwright"), "__version__", "unknown")
            browser = playwright.chromium.launch(headless=True, executable_path=browser_executable)
            environment['browser_executable'] = browser_executable or 'playwright-managed'
            environment["chromium"] = browser.version
            for viewport_name, viewport in VIEWPORTS.items():
                context = browser.new_context(
                    viewport=viewport,
                    device_scale_factor=1,
                    locale="ru-RU",
                    timezone_id="Asia/Krasnoyarsk",
                    color_scheme="light",
                    reduced_motion="reduce",
                    service_workers="block",
                )
                context.add_init_script("""() => {
                  const style = document.createElement('style');
                  style.textContent = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';
                  document.documentElement.appendChild(style);
                }""")
                try:
                    for source_page in source["pages"]:
                        route = source_page["public_route"]
                        page = context.new_page()
                        console_errors: list[str] = []
                        page_errors: list[str] = []
                        failed_requests: list[dict] = []
                        bad_responses: list[dict] = []
                        seen_dynamic: list[dict] = []

                        page.on("console", lambda msg, target=console_errors: target.append(msg.text) if msg.type == "error" else None)
                        page.on("pageerror", lambda exc, target=page_errors: target.append(str(exc)))

                        def on_request_failed(request, target=failed_requests):
                            parsed = urlparse(request.url)
                            target.append({"url": request.url, "path": parsed.path, "failure": request.failure})

                        def on_response(response, target=bad_responses):
                            parsed = urlparse(response.url)
                            if response.status >= 400:
                                target.append({"url": response.url, "path": parsed.path, "status": response.status})

                        page.on("requestfailed", on_request_failed)
                        page.on("response", on_response)

                        page.route("**/*", make_dynamic_route_handler(excluded, seen_dynamic, base, external_requests_observed))
                        try:
                            response = page.goto(base + route, wait_until="load", timeout=15000)
                            if source_page.get('expected_final_route', route) != route:
                                page.wait_for_url(base + source_page['expected_final_route'], wait_until='load', timeout=15000)
                            page.evaluate("document.fonts && document.fonts.ready")
                            lazy_images = materialize_lazy_images(page)
                            title = page.title()
                            h1 = page.locator("h1").all_inner_texts()
                            h1 = [normalized_text(value) for value in h1]
                            canonical = canonical_value(page)
                            metrics = page.evaluate("""() => ({
                              clientWidth: document.documentElement.clientWidth,
                              scrollWidth: document.documentElement.scrollWidth,
                              scrollHeight: document.documentElement.scrollHeight,
                              renderedText: document.body ? document.body.innerText : ''
                            })""")
                            overflow = metrics["scrollWidth"] - metrics["clientWidth"]
                            dynamic_requests_observed.extend(
                                {
                                    "public_route": route,
                                    "viewport": viewport_name,
                                    **item,
                                }
                                for item in seen_dynamic
                            )
                            effective_request_failures = [
                                item for item in failed_requests + bad_responses
                                if item.get("path") not in excluded or item.get("path") == "/app-script.php"
                            ]
                            checks = {
                                "navigation_status": response.status if response else None,
                                "final_route_match": page.url == base + source_page.get('expected_final_route', route),
                                "title_match": accepted_title_match(source_page, title),
                                "h1_match": h1 == source_page["h1"],
                                "canonical_match": canonical == source_page["canonical"],
                                "horizontal_overflow_px": overflow,
                                "horizontal_overflow_pass": overflow <= OVERFLOW_TOLERANCE_PX,
                                "console_errors": console_errors,
                                "page_errors": page_errors,
                                "failed_or_bad_requests": effective_request_failures,
                                "lazy_images": lazy_images,
                                "lazy_images_materialized": not lazy_images["unresolved"],
                            }
                            reasons = []
                            if checks["navigation_status"] != 200:
                                reasons.append("navigation_status")
                            for key in ("final_route_match", "title_match", "h1_match", "canonical_match", "horizontal_overflow_pass"):
                                if not checks[key]:
                                    reasons.append(key)
                            if console_errors:
                                reasons.append("console_errors")
                            if page_errors:
                                reasons.append("page_errors")
                            if effective_request_failures:
                                reasons.append("failed_or_bad_requests")
                            if not checks["lazy_images_materialized"]:
                                reasons.append("lazy_images_not_materialized")
                            screenshot_rel = Path("screenshots") / viewport_name / f"{source_page['route_registry_id']}.jpg"
                            screenshot_path = output / screenshot_rel
                            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                            page.screenshot(path=str(screenshot_path), full_page=True, type="jpeg", quality=84)
                            item = {
                                "public_route": route,
                                "source_path": source_page["source_path"],
                                "source_sha256": source_page["source_sha256"],
                                "source_ref": source_page.get("source_ref"),
                                "historical_source_sha256": source_page.get("historical_source_sha256"),
                                "render_source_path": source_page.get("render_source_path"),
                                "render_source_sha256": source_page.get("render_source_sha256"),
                                "expected_final_route": source_page.get("expected_final_route", route),
                                "observed_url": page.url,
                                "viewport": viewport_name,
                                "viewport_size": viewport,
                                "relative_path": screenshot_rel.as_posix(),
                                "sha256": sha256_file(screenshot_path),
                                "bytes": screenshot_path.stat().st_size,
                                "image_width": viewport["width"],
                                "image_height": metrics["scrollHeight"],
                                "rendered_visible_sha256": sha256_bytes(normalized_text(metrics["renderedText"]).encode()),
                                "checks": checks,
                                "status": "PASS" if not reasons else "FAIL",
                                "failure_reasons": reasons,
                            }
                            manifest.append(item)
                            print(f"[{len(manifest)}/{EXPECTED_PAGE_COUNT * len(VIEWPORTS)}] {viewport_name} {route}: {item['status']}", flush=True)
                            if reasons:
                                failures.append({"public_route": route, "viewport": viewport_name, "reasons": reasons})
                        except Exception as exc:
                            failures.append({"public_route": route, "viewport": viewport_name, "reasons": ["capture_exception"], "error": repr(exc)})
                        finally:
                            page.close()
                finally:
                    context.close()
            if browser:
                browser.close()
                browser = None

        expected_captures = EXPECTED_PAGE_COUNT * len(VIEWPORTS)
        expected_contact_sheets = len(VIEWPORTS) * 4
        contact_sheets = make_contact_sheets(output, manifest) if manifest else []
        if os.getenv("GITHUB_ACTIONS") == "true" and not environment["evidence_head_sha"]:
            failures.append({"scope": "lineage", "reasons": ["missing_evidence_head_sha"]})
        if len(manifest) == expected_captures and not failures and len(contact_sheets) == expected_contact_sheets:
            status = "PASS_BROWSER_RENDER_SNAPSHOT_ONLY"
    except Exception as exc:
        fatal_error = repr(exc)
        failures.append({"scope": "harness", "reasons": ["fatal_exception"], "error": fatal_error})
        contact_sheets = []
    finally:
        if browser:
            with contextlib.suppress(Exception):
                browser.close()
        if server:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        if "log_stream" in locals():
            log_stream.flush()
            os.fsync(log_stream.fileno())
            log_stream.close()

    report = {
        "schema_version": 1,
        "status": status,
        "scope": "accepted_static_pages_browser_render_only",
        "started_at": started,
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_report": {
            "path": report_path.relative_to(root).as_posix(),
            "sha256": sha256_bytes(raw) if raw else None,
        },
        "environment": environment,
        "viewports": VIEWPORTS,
        "counts": {
            "source_pages": EXPECTED_PAGE_COUNT,
            "expected_captures": EXPECTED_PAGE_COUNT * len(VIEWPORTS),
            "actual_captures": len(manifest),
            "failed_captures": len(failures),
            "contact_sheets": len(contact_sheets),
            "dynamic_requests_observed": len(dynamic_requests_observed),
            "dynamic_requests_stubbed": sum(
                item["disposition"] == "inert_204_stub_not_executed"
                for item in dynamic_requests_observed
            ),
            "dynamic_render_dependencies_allowed": sum(
                item["disposition"] == "allowed_render_dependency_not_accepted"
                for item in dynamic_requests_observed
            ),
        },
        "failures": failures,
        "dynamic_requests_observed": dynamic_requests_observed,
        "external_requests_observed": external_requests_observed,
        "acceptance_limits": {
            "browser_render_snapshot_accepted": status.startswith("PASS_"),
            "dynamic_endpoints_accepted": False,
            "external_services_accepted": False,
            "substantive_content_quality_accepted": False,
            "legal_accepted": False,
            "deploy_accepted": False,
            "release_accepted": False,
        },
        "fatal_error": fatal_error,
    }
    atomic_json(output / "manifest.json", manifest)
    atomic_json(output / "contact-sheets.json", contact_sheets)
    atomic_json(output / "report.json", report)
    receipt = {
        "status": status,
        "report_sha256": sha256_file(output / "report.json"),
        "manifest_sha256": sha256_file(output / "manifest.json"),
        "contact_sheets_sha256": sha256_file(output / "contact-sheets.json"),
        "php_log_sha256": sha256_file(log_path) if log_path.exists() else None,
        "checkpoint_policy": "verified_only",
        "model_calls": 0,
        "paid_api_calls": 0,
    }
    atomic_json(output / "receipt.json", receipt)
    return report, 0 if status.startswith("PASS_") else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path, default=Path("tools/reports/site-static-content-snapshot-20261012/report.json"))
    parser.add_argument("--output", type=Path, default=Path("browser-snapshot-artifact"))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--staging-source", action="store_true")
    parser.add_argument("--browser-executable", default=os.getenv('BROWSER_SNAPSHOT_EXECUTABLE') or None)
    args = parser.parse_args()
    root = args.root.resolve()
    report_path = args.report if args.report.is_absolute() else root / args.report
    if args.validate_only:
        source = validate_source_report(report_path.read_bytes())
        if args.staging_source:
            source = staging_render_source(source, root)
        print(f"source contract PASS: {len(source['pages'])} pages")
        return 0
    output = args.output if args.output.is_absolute() else root / args.output
    report, exit_code = capture(root, report_path, output, args.staging_source, args.browser_executable)
    print(json.dumps({"status": report["status"], "counts": report["counts"]}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
