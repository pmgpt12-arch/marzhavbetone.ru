#!/usr/bin/env python3
# Одноразовая оптимизация производительности (запускается из .github/workflows/perf-optimize.yml):
# 1. Собирает bundle.css из всех css-файлов в каноническом порядке и заменяет
#    на всех страницах набор <link rel=stylesheet> одной ссылкой на бандл.
# 2. Проставляет img-атрибуты: первой картинке страницы fetchpriority=high
#    (если это не lazy-картинка), остальным loading=lazy, всем decoding=async.
# 3. Сокращает title и og:title главной до 56 символов.
# 4. Пережимает assets/*.jpg (quality=82, progressive, optimize), если результат меньше.
# Все преобразования идемпотентны: повторный запуск ничего не меняет.

import hashlib
import os
import re
import sys

ROOT = os.getcwd()

CSS_ORDER = [
    'styles', 'catalog', 'product', 'article', 'faq', 'social-icons', 'lead',
    'footer', 'contact-form', 'cart', 'author', 'desktop', 'desktop-wide', 'legal',
]

# Обрабатываем только публичные страницы сайта. Служебные и внутренние
# каталоги пропускаем: там могут лежать фикстуры в не-UTF-8 кодировках.
SKIP_DIRS = {
    '.git', '.github', '.claude', 'node_modules', 'out', '.venv-frames',
    'content', 'data', 'docs', 'reports', 'research', 'tools',
    'products-storage', 'downloads', 'media',
}

OLD_TITLE = 'Шаблоны КС-2, КС-3 и документы для субподрядчиков — Маржа в бетоне'
NEW_TITLE = 'Шаблоны КС-2 и КС-3 для субподрядчиков — Маржа в бетоне'


def build_bundle():
    parts = []
    missing = []
    for name in CSS_ORDER:
        p = os.path.join(ROOT, name + '.css')
        if not os.path.exists(p):
            missing.append(name + '.css')
            continue
        with open(p, encoding='utf-8') as f:
            parts.append('/* ===== %s.css ===== */\n' % name + f.read())
    if missing:
        print('::error::Не найдены css: %s' % ', '.join(missing))
        sys.exit(1)
    bundle = '\n'.join(parts)
    # Версия совпадает по алгоритму с tools/asset_versions.py: sha1 содержимого.
    v = hashlib.sha1(bundle.encode()).hexdigest()[:8]
    with open(os.path.join(ROOT, 'bundle.css'), 'w', encoding='utf-8') as f:
        f.write(bundle)
    print('bundle.css: %d bytes, v=%s' % (len(bundle), v))
    return v


def iter_html():
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith('.html'):
                yield os.path.join(root, fn)


def transform_html(path, version):
    try:
        with open(path, encoding='utf-8') as f:
            h = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print('::warning::%s: HTML пропущен (%s)' % (path, e))
        return False
    orig = h

    bundle_tag = '<link rel="stylesheet" href="/bundle.css?v=%s">' % version
    links = list(re.finditer(r'<link rel="stylesheet" href="[^"]+\.css[^"]*">\s*\n?', h))
    if links:
        first_start = links[0].start()
        for m in reversed(links):
            h = h[:m.start()] + h[m.end():]
        h = h[:first_start] + bundle_tag + '\n' + h[first_start:]

    state = {'first': True}

    def fix_img(m):
        tag = m.group(0)
        add = ''
        if 'decoding=' not in tag:
            add += ' decoding="async"'
        if state['first']:
            state['first'] = False
            if 'fetchpriority=' not in tag and 'loading="lazy"' not in tag:
                add += ' fetchpriority="high"'
        else:
            if 'loading=' not in tag:
                add += ' loading="lazy"'
        if add:
            tag = tag.replace('<img', '<img' + add, 1)
        return tag

    h = re.sub(r'<img\b[^>]*>', fix_img, h)

    if os.path.basename(path) == 'index.html' and os.path.dirname(path) == ROOT:
        h = h.replace('<title>%s</title>' % OLD_TITLE,
                      '<title>%s</title>' % NEW_TITLE)
        h = h.replace('property="og:title" content="%s"' % OLD_TITLE,
                      'property="og:title" content="%s"' % NEW_TITLE)

    if h != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(h)
        return True
    return False


def recompress_images():
    try:
        from PIL import Image
    except ImportError:
        print('::error::Pillow не установлен')
        sys.exit(1)
    total_before = total_after = 0
    changed = 0
    assets = os.path.join(ROOT, 'assets')
    if not os.path.isdir(assets):
        return
    for fn in sorted(os.listdir(assets)):
        if not fn.lower().endswith(('.jpg', '.jpeg')):
            continue
        p = os.path.join(assets, fn)
        before = os.path.getsize(p)
        try:
            img = Image.open(p)
            img = img.convert('RGB')
            buf = os.path.join(assets, fn + '.tmp')
            img.save(buf, 'JPEG', quality=82, optimize=True, progressive=True)
            after = os.path.getsize(buf)
            if after < before:
                os.replace(buf, p)
                changed += 1
                total_before += before
                total_after += after
            else:
                os.remove(buf)
        except Exception as e:
            print('::warning::%s: %s' % (fn, e))
    print('images: %d пережато, %d KB -> %d KB' % (changed, total_before // 1024, total_after // 1024))


def main():
    version = build_bundle()
    n = 0
    for p in iter_html():
        if transform_html(p, version):
            n += 1
    print('html: %d страниц обновлено' % n)
    recompress_images()


if __name__ == '__main__':
    main()
