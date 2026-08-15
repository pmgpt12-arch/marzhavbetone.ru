#!/usr/bin/env python3
"""Приёмочный аудит боевого сайта после правок вёрстки: настоящий рендер.

Зачем отдельно от `check_mobile.py`: тот поднимает локальный сервер и
проверяет файлы репозитория на одной ширине. Здесь меряется то, что
боевой сервер отдаёт браузеру, на пяти ширинах сразу, и вопрос другой —
не «сломалось ли меню», а «на что похожа страница целиком».

Что снимается на каждой ширине:
  · полноэкранный снимок;
  · scrollHeight, innerHeight, отношение (сколько экранов листать);
  · scrollWidth и clientWidth документа — горизонтальный вылет;
  · поэлементный вылет: scrollWidth > clientWidth, right > ширины окна,
    left < 0, содержимое, обрезанное фиксированной высотой;
  · фактический порядок блоков сверху вниз с отступом каждого от верха
    в экранах — на этом считается, далеко ли блок от первого экрана;
  · признаки настольной вёрстки: ширина колонки контента против ширины
    окна, число колонок в сетках. Растянутая мобильная версия отличается
    от настольной именно этим, и отличие меряется, а не оценивается на
    глаз.

Отдельными файлами — ссылки главной с кодами ответа и цепочками
переадресаций и поисковый слой: robots.txt, sitemap.xml, canonical,
заголовок, описание, число H1.

Ничего не чинит и ничего не утверждает про качество: инструмент отдаёт
числа и снимки, оценку даёт человек или отчёт поверх этих чисел.

Запуск:
    python3 tools/audit_after_redesign.py --url https://marzhavbetone.ru/ \
        --out-dir audit-after-redesign

Нужен playwright с хромиумом. Без него — код возврата 2 и слово
«не запускалась», а не «прошла».
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Пять ширин задания. Имя файла снимка закреплено: по нему отчёт ищет
# картинку, и переименование здесь тихо ломает связь отчёта со снимком.
VIEWPORTS = [
    {"name": "mobile-390", "width": 390, "height": 844, "kind": "mobile"},
    {"name": "mobile-430", "width": 430, "height": 932, "kind": "mobile"},
    {"name": "desktop-1366", "width": 1366, "height": 768, "kind": "desktop"},
    {"name": "desktop-1440", "width": 1440, "height": 900, "kind": "desktop"},
    {"name": "desktop-1920", "width": 1920, "height": 1080, "kind": "desktop"},
]

# Допуск в пикселях. Округление субпиксельных размеров даёт разницу в
# доли пикселя на каждом втором элементе; порог 1px отсекает шум и
# оставляет настоящий вылет.
SLACK = 1.0

UA = "Mozilla/5.0 (compatible; marzhavbetone-audit/1.0)"

# Внутренние коды линейки. В клиентском интерфейсе их быть не должно:
# покупатель их не знает, а нам они говорят о протёкшей внутренней
# номенклатуре. Границы слова обязательны — иначе «P1» найдётся в любом
# «P10» и в хэше картинки.
INTERNAL_CODE_RE = re.compile(r"(?<![A-Za-zА-Яа-я0-9])([PTК]\d{1,2})(?![A-Za-zА-Яа-я0-9])")

MEASURE_JS = r"""
() => {
  const SLACK = 1.0;
  const vw = document.documentElement.clientWidth;
  const vh = window.innerHeight;

  const shortPath = (el) => {
    const bits = [];
    let node = el;
    for (let depth = 0; node && node.nodeType === 1 && depth < 4; depth++) {
      let bit = node.tagName.toLowerCase();
      if (node.id) { bits.unshift(bit + '#' + node.id); break; }
      const cls = (node.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
      if (cls.length) bit += '.' + cls.join('.');
      bits.unshift(bit);
      node = node.parentElement;
    }
    return bits.join(' > ');
  };

  const hiddenByAncestor = (el) => {
    for (let n = el; n; n = n.parentElement) {
      if (n.hasAttribute && (n.hasAttribute('hidden') || n.getAttribute('aria-hidden') === 'true')) return true;
    }
    return false;
  };

  const CATEGORIES = [
    ['product-card', '.solution-card, .product-card, .pack-card, [class*="solution"], [class*="product"]'],
    ['case-card', '[class*="case"], [id*="case"], [class*="keys"], [class*="dossier"]'],
    ['article-card', '.material-card, .topic-grid article, [class*="article"], [class*="material"]'],
    ['button', 'button, .button, a.button, [role="button"], input[type="submit"]'],
    ['badge', '.eyebrow, .badge, .tag, [class*="badge"], [class*="label"]'],
    ['price', '[class*="price"], [class*="cost"], [class*="total"]'],
    ['header', 'header, header *'],
    ['footer', 'footer, footer *'],
  ];
  const categoryOf = (el) => {
    const hits = [];
    for (const [name, sel] of CATEGORIES) {
      try { if (el.matches(sel)) hits.push(name); } catch (e) { /* селектор не поддержан */ }
    }
    return hits;
  };

  // --- поэлементный вылет ------------------------------------------------
  const overflow = [];
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;

    const reasons = [];
    const scrollsX = cs.overflowX === 'auto' || cs.overflowX === 'scroll';
    const scrollsY = cs.overflowY === 'auto' || cs.overflowY === 'scroll';

    if (el.scrollWidth > el.clientWidth + SLACK && !scrollsX && el.clientWidth > 0) {
      reasons.push('scrollWidth>clientWidth');
    }
    if (r.right > vw + SLACK) reasons.push('right>viewport');
    if (r.left < -SLACK) reasons.push('left<0');
    // Фиксированная высота, режущая содержимое: высота задана не auto,
    // содержимое выше, и прокрутки у элемента нет.
    if (cs.height !== 'auto' && el.scrollHeight > el.clientHeight + SLACK
        && !scrollsY && el.clientHeight > 0 && el.children.length + el.textContent.trim().length > 0) {
      reasons.push('fixed-height-clip');
    }
    if (!reasons.length) continue;

    overflow.push({
      path: shortPath(el),
      tag: el.tagName.toLowerCase(),
      categories: categoryOf(el),
      reasons,
      rect: {left: Math.round(r.left), right: Math.round(r.right),
             top: Math.round(r.top + window.scrollY), width: Math.round(r.width),
             height: Math.round(r.height)},
      scrollWidth: el.scrollWidth, clientWidth: el.clientWidth,
      scrollHeight: el.scrollHeight, clientHeight: el.clientHeight,
      position: cs.position,
      hidden_branch: hiddenByAncestor(el),
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80),
    });
    if (overflow.length >= 400) break;
  }

  // --- порядок блоков ----------------------------------------------------
  const blocks = [];
  const roots = document.querySelectorAll('body > header, main > section, body > section, body > footer, main > *[class*="section"]');
  let idx = 0;
  for (const el of roots) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none') continue;
    const r = el.getBoundingClientRect();
    const top = Math.round(r.top + window.scrollY);
    const heading = el.querySelector('h1, h2');
    const eyebrow = el.querySelector('.eyebrow');
    blocks.push({
      order: idx++,
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      class: el.getAttribute('class') || null,
      eyebrow: eyebrow ? eyebrow.textContent.trim().slice(0, 60) : null,
      heading: heading ? heading.textContent.trim().replace(/\s+/g, ' ').slice(0, 90) : null,
      heading_level: heading ? heading.tagName.toLowerCase() : null,
      top,
      height: Math.round(r.height),
      screens_from_top: +(top / vh).toFixed(2),
      links: el.querySelectorAll('a[href]').length,
      images: el.querySelectorAll('img').length,
    });
  }

  // --- признаки настольной вёрстки ---------------------------------------
  // Растянутая мобильная версия — это одна колонка во всю ширину окна.
  // Меряем: сколько занимает самая широкая колонка контента и сколько
  // колонок в сетках выше первого экрана.
  const grids = [];
  for (const el of document.querySelectorAll('main *')) {
    const cs = getComputedStyle(el);
    if (cs.display !== 'grid' && cs.display !== 'flex') continue;
    const kids = Array.from(el.children).filter(k => getComputedStyle(k).display !== 'none');
    if (kids.length < 2) continue;
    const tops = new Set(kids.map(k => Math.round(k.getBoundingClientRect().top)));
    const cols = Math.round(kids.length / Math.max(tops.size, 1));
    if (cols < 1) continue;
    grids.push({
      path: shortPath(el), display: cs.display, children: kids.length,
      rows: tops.size, columns_per_row: cols,
      template: cs.gridTemplateColumns && cs.gridTemplateColumns !== 'none'
        ? cs.gridTemplateColumns.split(' ').length : null,
      width: Math.round(el.getBoundingClientRect().width),
    });
    if (grids.length >= 60) break;
  }

  const main = document.querySelector('main');
  const mainWidth = main ? Math.round(main.getBoundingClientRect().width) : null;
  // Самый широкий «текстовый» контейнер: по нему видно, ограничена ли
  // строка или тянется во всю ширину монитора.
  let widestText = 0;
  for (const el of document.querySelectorAll('main p, main h1, main h2, main li')) {
    const w = el.getBoundingClientRect().width;
    if (w > widestText) widestText = w;
  }

  const bodyFont = getComputedStyle(document.body).fontSize;

  // --- ссылки ------------------------------------------------------------
  const anchors = [];
  for (const a of document.querySelectorAll('a[href]')) {
    const sect = a.closest('section, header, footer');
    const r = a.getBoundingClientRect();
    anchors.push({
      href: a.getAttribute('href'),
      resolved: a.href || null,
      text: (a.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60),
      section: sect ? (sect.id || (sect.getAttribute('class') || sect.tagName.toLowerCase())) : null,
      top: Math.round(r.top + window.scrollY),
      target_blank: a.target === '_blank',
    });
  }

  // --- продукты и внутренние коды ----------------------------------------
  const productCards = document.querySelectorAll(
    '.solution-card, .product-card, .pack-card, [class*="solution-card"], [class*="product-card"]').length;
  const tableRows = document.querySelectorAll('main table tr').length;
  const bodyText = (document.body.innerText || '').replace(/\s+/g, ' ');
  const fileMentions = (bodyText.match(/\.(docx|xlsx|pdf|doc|xls)\b/gi) || []).length;

  const ids = Array.from(document.querySelectorAll('[id]')).map(el => el.id);

  return {
    doc: {
      scrollHeight: document.documentElement.scrollHeight,
      innerHeight: vh,
      screens: +(document.documentElement.scrollHeight / vh).toFixed(2),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: vw,
      horizontal_overflow: document.documentElement.scrollWidth > vw + SLACK,
      horizontal_overflow_px: Math.max(0, document.documentElement.scrollWidth - vw),
      body_scrollWidth: document.body.scrollWidth,
    },
    layout: {
      main_width: mainWidth,
      main_width_share: mainWidth ? +(mainWidth / vw).toFixed(3) : null,
      widest_text_block: Math.round(widestText),
      widest_text_share: +(widestText / vw).toFixed(3),
      body_font_size: bodyFont,
      grids,
    },
    blocks,
    overflow,
    anchors,
    products: {
      product_cards: productCards,
      table_rows: tableRows,
      file_extension_mentions: fileMentions,
    },
    text: bodyText.slice(0, 200000),
    element_ids: ids,
    title: document.title,
    h1: Array.from(document.querySelectorAll('h1')).map(h => h.textContent.trim().slice(0, 120)),
    canonical: (document.querySelector('link[rel="canonical"]') || {}).href || null,
    meta_robots: (document.querySelector('meta[name="robots"]') || {}).content || null,
    meta_description: (document.querySelector('meta[name="description"]') || {}).content || null,
  };
}
"""


def http_probe(url: str, max_hops: int = 6) -> dict:
    """Код ответа и цепочка переадресаций. Переадресации разматываются
    вручную: цепочка — часть замера, а не помеха ему."""
    chain: list[dict] = []
    current = url
    for _ in range(max_hops):
        req = urllib.request.Request(current, headers={"User-Agent": UA}, method="GET")

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):  # noqa: D401
                return None

        opener = urllib.request.build_opener(NoRedirect)
        try:
            with opener.open(req, timeout=25) as resp:
                chain.append({"url": current, "status": resp.status})
                return {"url": url, "status": resp.status, "chain": chain,
                        "final": current, "error": None,
                        "headers": {k.lower(): v for k, v in resp.headers.items()
                                    if k.lower() in ("content-type", "location", "server",
                                                     "last-modified", "etag", "cache-control",
                                                     "content-length")}}
        except urllib.error.HTTPError as exc:
            chain.append({"url": current, "status": exc.code})
            location = exc.headers.get("Location") if exc.headers else None
            if exc.code in (301, 302, 303, 307, 308) and location:
                current = urllib.parse.urljoin(current, location)
                continue
            return {"url": url, "status": exc.code, "chain": chain, "final": current,
                    "error": None, "headers": {}}
        except Exception as exc:  # сеть, TLS, имя — всё это результат замера
            chain.append({"url": current, "status": None})
            return {"url": url, "status": None, "chain": chain, "final": current,
                    "error": f"{type(exc).__name__}: {exc}", "headers": {}}
    return {"url": url, "status": None, "chain": chain, "final": current,
            "error": "too many redirects", "headers": {}}


def fetch_text(url: str) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception:
        return None, ""


def audit_links(measure: dict, base_url: str) -> dict:
    """Каждая внутренняя цель — один запрос. Внешние адреса не трогаем:
    их доступность не про нашу выкладку."""
    host = urllib.parse.urlparse(base_url).netloc
    page_ids = set(measure["element_ids"])
    anchors = measure["anchors"]

    empty = [a for a in anchors if not (a["href"] or "").strip()]
    bad_anchor = []
    internal: dict[str, list[dict]] = {}
    external = []

    for a in anchors:
        href = (a["href"] or "").strip()
        if not href:
            continue
        if href.startswith("#"):
            target = href[1:]
            if target and target not in page_ids:
                bad_anchor.append(a)
            continue
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        resolved = a["resolved"] or urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(resolved)
        if parsed.netloc != host:
            external.append(a)
            continue
        if parsed.fragment:
            resolved = resolved.split("#", 1)[0]
        internal.setdefault(resolved, []).append(a)

    checked = []
    for url in sorted(internal):
        probe = http_probe(url)
        probe["found_in"] = sorted({a["section"] or "—" for a in internal[url]})
        probe["anchor_texts"] = sorted({a["text"] for a in internal[url]})[:4]
        probe["occurrences"] = len(internal[url])
        checked.append(probe)

    return {
        "base": base_url,
        "total_anchors": len(anchors),
        "unique_internal": len(internal),
        "external_count": len(external),
        "empty_href": empty,
        "bad_fragment": bad_anchor,
        "checked": checked,
        "broken": [c for c in checked if c["status"] is None or c["status"] >= 400],
        "redirects": [c for c in checked if len(c["chain"]) > 1],
    }


def audit_seo(measure: dict, base_url: str, repo_root: Path) -> dict:
    root = f"{urllib.parse.urlparse(base_url).scheme}://{urllib.parse.urlparse(base_url).netloc}"
    home = http_probe(base_url)
    index_html = http_probe(urllib.parse.urljoin(root + "/", "index.html"))
    robots_code, robots_body = fetch_text(root + "/robots.txt")
    sitemap_code, sitemap_body = fetch_text(root + "/sitemap.xml")

    live_urls = sorted(set(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap_body)))
    repo_sitemap = repo_root / "sitemap.xml"
    repo_urls: list[str] = []
    if repo_sitemap.exists():
        repo_urls = sorted(set(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>",
                                          repo_sitemap.read_text("utf-8", "replace"))))

    return {
        "home": {"status": home["status"], "chain": home["chain"], "headers": home["headers"]},
        "index_html": {"status": index_html["status"], "chain": index_html["chain"]},
        "robots_txt": {"status": robots_code,
                       "has_sitemap_line": "sitemap" in robots_body.lower(),
                       "disallow_all": bool(re.search(r"(?im)^disallow:\s*/\s*$", robots_body)),
                       "body": robots_body[:1500]},
        "sitemap_xml": {"status": sitemap_code, "url_count": len(live_urls)},
        "canonical": measure["canonical"],
        "canonical_matches_home": (measure["canonical"] or "").rstrip("/") == base_url.rstrip("/"),
        "meta_robots": measure["meta_robots"],
        "noindex": "noindex" in (measure["meta_robots"] or "").lower(),
        "title": measure["title"],
        "title_length": len(measure["title"] or ""),
        "description": measure["meta_description"],
        "description_length": len(measure["meta_description"] or ""),
        "h1_count": len(measure["h1"]),
        "h1": measure["h1"],
        "sitemap_live_urls": live_urls,
        "sitemap_repo_urls": repo_urls,
        "sitemap_only_live": sorted(set(live_urls) - set(repo_urls)),
        "sitemap_only_repo": sorted(set(repo_urls) - set(live_urls)),
    }


def run(url: str, out_dir: Path, repo_root: Path) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("НЕ ЗАПУСКАЛАСЬ: нет playwright. Установка: pip install playwright "
              "&& playwright install chromium", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    measurements: dict = {
        "url": url,
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "viewports": {},
    }
    overflow_all: dict = {}
    reference: dict | None = None

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp in VIEWPORTS:
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=1,
                user_agent=UA,
                is_mobile=vp["kind"] == "mobile",
                has_touch=vp["kind"] == "mobile",
            )
            page = context.new_page()
            # networkidle точнее, но на странице со счётчиком он иногда не
            # наступает вовсе. Тогда берём load: замер важнее ожидания.
            try:
                page.goto(url, wait_until="networkidle", timeout=45_000)
            except Exception as exc:
                print(f"{vp['name']}: networkidle не наступил ({type(exc).__name__}), "
                      f"повтор по load", file=sys.stderr)
                page.goto(url, wait_until="load", timeout=45_000)
            page.wait_for_timeout(1200)  # дать сработать отложенным картинкам
            # Проматываем до конца и обратно: без этого lazy-картинки не
            # догружаются, и высота страницы меряется меньше настоящей.
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1200)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(400)

            data = page.evaluate(MEASURE_JS)
            shot = out_dir / f"{vp['name']}-full.png"
            page.screenshot(path=str(shot), full_page=True)

            measurements["viewports"][vp["name"]] = {
                "width": vp["width"], "height": vp["height"], "kind": vp["kind"],
                "doc": data["doc"], "layout": data["layout"], "blocks": data["blocks"],
                "products": data["products"],
                "overflow_count": len(data["overflow"]),
                "screenshot": shot.name,
            }
            overflow_all[vp["name"]] = data["overflow"]
            if vp["name"] == "desktop-1440":
                reference = data
            context.close()
        browser.close()

    assert reference is not None
    links = audit_links(reference, url)
    seo = audit_seo(reference, url, repo_root)

    body_text = reference["text"]
    codes = sorted(set(INTERNAL_CODE_RE.findall(body_text)))
    measurements["client_ui"] = {
        "internal_codes_found": codes,
        "product_cards": reference["products"]["product_cards"],
        "table_rows_in_main": reference["products"]["table_rows"],
        "file_extension_mentions": reference["products"]["file_extension_mentions"],
        "page_text_length": len(body_text),
    }
    measurements["html_bytes"] = None

    (out_dir / "measurements.json").write_text(
        json.dumps(measurements, ensure_ascii=False, indent=2), "utf-8")
    (out_dir / "overflow.json").write_text(
        json.dumps(overflow_all, ensure_ascii=False, indent=2), "utf-8")
    (out_dir / "links.json").write_text(
        json.dumps(links, ensure_ascii=False, indent=2), "utf-8")
    (out_dir / "seo.json").write_text(
        json.dumps(seo, ensure_ascii=False, indent=2), "utf-8")
    (out_dir / "page-text.txt").write_text(body_text, "utf-8")

    print_summary(measurements, overflow_all, links, seo)
    return 0


def print_summary(measurements: dict, overflow_all: dict, links: dict, seo: dict) -> None:
    """Сводка в лог прогона. Артефакт скачивают не всегда, а лог виден
    сразу — числа, по которым выносится вердикт, должны быть в нём."""
    print("\n=== РАЗМЕРЫ СТРАНИЦЫ ===")
    print(f"{'viewport':<14}{'scrollH':>9}{'innerH':>8}{'экранов':>9}"
          f"{'scrollW':>9}{'clientW':>9}  гор.вылет")
    for name, vp in measurements["viewports"].items():
        d = vp["doc"]
        flag = f"ДА +{d['horizontal_overflow_px']}px" if d["horizontal_overflow"] else "нет"
        print(f"{name:<14}{d['scrollHeight']:>9}{d['innerHeight']:>8}{d['screens']:>9}"
              f"{d['scrollWidth']:>9}{d['clientWidth']:>9}  {flag}")

    print("\n=== ВЁРСТКА: ширина контента против окна ===")
    for name, vp in measurements["viewports"].items():
        lay = vp["layout"]
        multi = [g for g in lay["grids"] if g["columns_per_row"] >= 2]
        print(f"{name:<14} main {lay['main_width']}px "
              f"({lay['main_width_share']} окна), самый широкий текст "
              f"{lay['widest_text_block']}px ({lay['widest_text_share']}), "
              f"сеток в 2+ колонки: {len(multi)} из {len(lay['grids'])}, "
              f"базовый шрифт {lay['body_font_size']}")

    print("\n=== ПОРЯДОК БЛОКОВ (1440) ===")
    ref = measurements["viewports"]["desktop-1440"]
    print(f"{'#':<3}{'экранов':>8}  {'высота':>7}  блок")
    for b in ref["blocks"]:
        label = b["id"] or (b["class"] or b["tag"])
        head = f" · {b['eyebrow']} / {b['heading']}" if (b["eyebrow"] or b["heading"]) else ""
        print(f"{b['order']:<3}{b['screens_from_top']:>8}  {b['height']:>7}  {label}{head}")

    print("\n=== ВЫЛЕТ ЭЛЕМЕНТОВ ===")
    for name, items in overflow_all.items():
        contributing = [i for i in items if not i["hidden_branch"]]
        print(f"{name:<14} всего {len(items):>3}, из них в видимой ветке "
              f"{len(contributing):>3}")
        for item in contributing[:12]:
            cats = ",".join(item["categories"]) or "—"
            print(f"    {'+'.join(item['reasons']):<42} {cats:<24} {item['path']}")
        if len(contributing) > 12:
            print(f"    … ещё {len(contributing) - 12}")

    print("\n=== ССЫЛКИ ===")
    print(f"всего якорей {links['total_anchors']}, уникальных внутренних "
          f"{links['unique_internal']}, внешних {links['external_count']}")
    print(f"пустой href: {len(links['empty_href'])}, "
          f"якорь в никуда: {len(links['bad_fragment'])}, "
          f"битых: {len(links['broken'])}, с переадресацией: {len(links['redirects'])}")
    for c in links["broken"]:
        print(f"    БИТАЯ {c['status']} {c['url']} ← {', '.join(c['found_in'])}")
    for c in links["redirects"]:
        hops = " → ".join(f"{h['status']}" for h in c["chain"])
        print(f"    ПЕРЕАДРЕСАЦИЯ {hops} {c['url']} → {c['final']}")
    for a in links["bad_fragment"]:
        print(f"    ЯКОРЬ В НИКУДА {a['href']} «{a['text']}»")

    print("\n=== ПОИСКОВЫЙ СЛОЙ ===")
    print(f"/ → {seo['home']['status']}, /index.html → {seo['index_html']['status']}")
    print(f"robots.txt → {seo['robots_txt']['status']}, "
          f"строка Sitemap: {seo['robots_txt']['has_sitemap_line']}, "
          f"Disallow: / — {seo['robots_txt']['disallow_all']}")
    print(f"sitemap.xml → {seo['sitemap_xml']['status']}, адресов "
          f"{seo['sitemap_xml']['url_count']}")
    print(f"canonical: {seo['canonical']} (совпадает с главной: "
          f"{seo['canonical_matches_home']})")
    print(f"meta robots: {seo['meta_robots']}, noindex: {seo['noindex']}")
    print(f"H1: {seo['h1_count']} — {seo['h1']}")
    print(f"title ({seo['title_length']}): {seo['title']}")
    print(f"description ({seo['description_length']}): {seo['description']}")
    print(f"в карте, но не в репозитории: {len(seo['sitemap_only_live'])}")
    for u in seo["sitemap_only_live"][:10]:
        print(f"    {u}")
    print(f"в репозитории, но не в карте: {len(seo['sitemap_only_repo'])}")
    for u in seo["sitemap_only_repo"][:10]:
        print(f"    {u}")

    print("\n=== КЛИЕНТСКИЙ ИНТЕРФЕЙС ===")
    ui = measurements["client_ui"]
    print(f"карточек продуктов: {ui['product_cards']}, строк таблиц в main: "
          f"{ui['table_rows_in_main']}, упоминаний файлов (.docx/.xlsx/.pdf): "
          f"{ui['file_extension_mentions']}")
    print(f"внутренние коды в тексте страницы: "
          f"{ui['internal_codes_found'] or 'не найдены'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="https://marzhavbetone.ru/")
    parser.add_argument("--out-dir", default="audit-after-redesign")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    return run(args.url, Path(args.out_dir), repo_root)


if __name__ == "__main__":
    sys.exit(main())
