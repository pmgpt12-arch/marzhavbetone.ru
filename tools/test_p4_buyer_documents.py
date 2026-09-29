#!/usr/bin/env python3
"""Документы P4 в архиве покупателя описывают только P4 и своё назначение.

Класс ошибки: шаблон, повторно использованный из другого SKU, приносит в
выдачу чужой контекст, служебную метку или неподтверждённое обещание —
и покупатель получает документ с неверным назначением.

В P4 так вышло трижды (MB001-R2-P4-R3, Baseline в
`tools/candidates/MB001_R2_P4_DOCUMENTS_R3.md`):

- `41`–`43` скопированы из P12 вместе с рамкой «Важно»: «типовые шаблоны для
  досудебного ответа на претензии», «возврат удержанного это другой
  комплект», «в претензии есть ссылки на проверки…». P4 — про ИД, передачу
  фронта и входной контроль;
- `03` обещает, что типовые замечания «встречаются в 80% случаев», —
  источника у доли нет; п. 7 «Стратегии» называл 30 дней молчания заказчика
  основанием для суда — по Р-026 (`MB001_R026_P4_R4_REVIEW.md` §1.5, коммит
  `b793ed9`) пункт заменён точным текстом `П7_Р026`;
- `31`–`34` несут колонтитулы генератора G1: «МАРЖА В БЕТОНЕ / РАБОЧИЙ
  ШАБЛОН» сверху и «<название> • версия 21.07.2026 • marzhavbetone.ru» снизу —
  марка продавца и служебная версия на документе второй стороны.

Проверяется не папка, а то, что уходит покупателю: архив собирает настоящая
PHP-функция `mvb_build_product_zip('p4')`. Нет PHP или сборщика — ошибка,
а не пропуск: без них фактическую выдачу не проверить.

Ищутся только точные фразы из Baseline, а не слова вроде «80%» или
«претензия»: голое слово ловит и законный текст.

    python3 -m pytest -q tools/test_p4_buyer_documents.py
    python3 tools/test_p4_buyer_documents.py
"""
from __future__ import annotations

import functools
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    import pytest
except ImportError:                                       # запуск без pytest
    pytest = None

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import build_preview                                      # noqa: E402
from test_delivery_artifacts import P4, P4_СОСТАВ, P4_СТРАНИЦА  # noqa: E402

# Текстовые части .docx, в которых покупатель может увидеть строку: тело,
# колонтитулы, примечания, сноски и свойства файла.
ЧАСТЬ = re.compile(
    r"^(word/(document|header\d*|footer\d*|comments\w*|footnotes|endnotes)\.xml"
    r"|docProps/(core|app|custom)\.xml)$")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Baseline: файл → точные фразы, которые покупателю уходить не должны.
# Это и только это — паттерны теста.
P12_РАМКА = (
    "Это типовые шаблоны для досудебного ответа на претензии заказчика/генподрядчика",
    "не гарантия того, что претензию снимут",
    "Комплект помогает не согласиться письменно и в срок — пока молчание или "
    "акт сверки без оговорок не превратились в согласие",
    "деньги уже удержаны или списаны — возврат удержанного это другой комплект "
    "и другая работа",
    "в претензии есть ссылки на проверки государственных органов или признаки "
    "уголовного дела",
)
КОЛОНТИТУЛ_G1 = "МАРЖА В БЕТОНЕ  /  РАБОЧИЙ ШАБЛОН"
BASELINE: dict[str, tuple[str, ...]] = {
    "03-perechen-vozmozhnyh-zamechaniy.docx": (
        "Типовые замечания (встречаются в 80% случаев)",
        "Фиксируйте сроки: если заказчик не отвечает на ваш ответ 30 дней - это "
        "основание для обращения в суд."),
    "31-pyat-aktov-skrytyh-rabot.docx": (
        КОЛОНТИТУЛ_G1,
        "Пять заготовок актов скрываемых работ  •  версия 21.07.2026  •  marzhavbetone.ru"),
    "32-shablon-ispolnitelnoy-shemy.docx": (
        КОЛОНТИТУЛ_G1,
        "Карточка исполнительной схемы  •  версия 21.07.2026  •  marzhavbetone.ru"),
    "33-akt-peredachi-komplekta-pto.docx": (
        КОЛОНТИТУЛ_G1,
        "Акт передачи комплекта ПТО  •  версия 21.07.2026  •  marzhavbetone.ru"),
    "34-sluzhebnaya-zapiska.docx": (
        КОЛОНТИТУЛ_G1,
        "Служебная записка о готовности и рисках  •  версия 21.07.2026  •  marzhavbetone.ru"),
    "41-akt-peredachi-ploshchadki-fronta.docx": P12_РАМКА,
    "42-akt-vhodnogo-kontrolya-materialov.docx": P12_РАМКА,
    "43-preduprezhdenie-po-st-716.docx": P12_РАМКА,
}
# Р-026 §1.5: п. 7 «Стратегии ответа на замечания» в `03` — ровно этот абзац
П7_Р026 = (
    "Фиксируйте сроки: срок ответа на замечания и претензионный порядок берите из "
    "договора. Молчание заказчика на ваш ответ само по себе не означает ни согласия "
    "с ним (если договор не говорит иного), ни права сразу идти в суд. Если работы "
    "не оплачены, сначала направьте претензию с требованием оплаты. Иск подавайте не "
    "раньше срока, который договор отводит на ответ на претензию, а если договор его "
    "не устанавливает, не раньше срока по ч. 5 ст. 4 АПК РФ, считая со дня "
    "направления претензии. Перед иском обратитесь к юристу.")
# STOP-P4-R3-N: файл, который по условию задачи не правится, — строгий xfail
# с номером и причиной. Молча файл из проверки не выпадает.
STOP: dict[str, str] = {}

КАВЫЧКИ = str.maketrans({c: '"' for c in "«»“”„‟\"'‘’‚"})


def нормализовать(текст: str) -> str:
    """Регистр, ё, кавычки и пробелы — к одному виду."""
    текст = текст.casefold().replace("ё", "е").translate(КАВЫЧКИ)
    return re.sub(r"\s+", " ", текст.replace(" ", " ")).strip()


def текст_части(xml: bytes) -> str:
    """Текст XML-части: runs абзаца склеены, абзацы — через перевод строки."""
    корень = ET.fromstring(xml)
    абзацы = list(корень.iter(W + "p"))
    if not абзацы:
        return " ".join(корень.itertext())
    return "\n".join(
        "".join(t.text or "" for t in п.iter() if t.tag in (W + "t", W + "delText"))
        for п in абзацы)


def части(docx: bytes) -> dict[str, str]:
    """Нормализованный текст каждой текстовой части .docx."""
    with zipfile.ZipFile(BytesIO(docx)) as z:
        return {n: нормализовать(текст_части(z.read(n)))
                for n in z.namelist() if ЧАСТЬ.match(n)}


@functools.lru_cache(maxsize=1)
def архив_p4() -> dict[str, bytes]:
    """Архив P4, собранный настоящей `mvb_build_product_zip('p4')`."""
    php = shutil.which("php")
    assert php, "PHP не найден: архив покупателя P4 не собрать — это ошибка, не пропуск"
    with tempfile.TemporaryDirectory() as tmp:
        код = r"""<?php
$tmp = $argv[1];
foreach ([
    'ORDERS_DIR' => $tmp, 'DELIVERY_DIR' => $tmp . '/delivery',
    'PRODUCTS_DIR' => $argv[2] . '/products-storage',
    'SITE_URL' => 'https://example.invalid', 'ADMIN_EMAIL' => 'a@example.invalid',
    'DELIVERY_TTL_DAYS' => 7, 'YOOKASSA_SHOP_ID' => 't', 'YOOKASSA_SECRET_KEY' => 't',
    'YOOKASSA_API_URL' => 'https://example.invalid', 'YOOKASSA_MODE' => 'test',
] as $name => $value) { define($name, $value); }
mkdir(DELIVERY_DIR, 0755, true);
require $argv[2] . '/products-config.php';
$path = mvb_build_product_zip('p4');
if ($path === null) { fwrite(STDERR, "mvb_build_product_zip('p4') вернула null\n"); exit(1); }
echo $path;
"""
        скрипт = Path(tmp) / "build.php"
        скрипт.write_text(код, encoding="utf-8")
        r = subprocess.run([php, str(скрипт), tmp, str(ROOT)],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, f"PHP-сборка P4 упала: {r.stderr or r.stdout}"
        with zipfile.ZipFile(r.stdout.strip()) as z:
            return {i.filename: z.read(i.filename) for i in z.infolist() if not i.is_dir()}


def test_p4_архив_собран_php_и_состав_23_файла() -> None:
    архив = архив_p4()
    assert sorted(архив) == sorted(P4_СОСТАВ), (
        f"архив P4: лишние {sorted(set(архив) - set(P4_СОСТАВ))}, "
        f"нет {sorted(set(P4_СОСТАВ) - set(архив))}")
    assert len(архив) == 23
    assert "43-preduprezhdenie-po-st-716.docx" in архив
    for имя, данные in архив.items():
        assert данные == (P4 / имя).read_bytes(), f"{имя}: в архиве не то, что в папке выдачи"


def проверить_baseline(имя: str) -> None:
    найдено = []
    for часть, текст in части(архив_p4()[имя]).items():
        найдено += [f"{часть}: «{фраза}»" for фраза in BASELINE[имя]
                    if нормализовать(фраза) in текст]
    assert not найдено, (f"{имя} в архиве P4 несёт чужой контекст или служебную "
                         "метку из Baseline:\n  " + "\n  ".join(найдено))


def случаи_baseline() -> list:
    if pytest is None:
        return list(BASELINE)
    return [pytest.param(имя, marks=pytest.mark.xfail(strict=True, reason=STOP[имя]))
            if имя in STOP else имя for имя in BASELINE]


if pytest is not None:
    @pytest.mark.parametrize("имя", случаи_baseline())
    def test_p4_документ_без_baseline_фраз(имя: str) -> None:
        проверить_baseline(имя)


def test_p4_03_пункт_7_по_р026() -> None:
    """Седьмой пункт «Стратегии» в `03` из архива — дословно текст Р-026 §1.5,
    отдельным абзацем, один раз."""
    with zipfile.ZipFile(BytesIO(архив_p4()["03-perechen-vozmozhnyh-zamechaniy.docx"])) as z:
        абзацы = текст_части(z.read("word/document.xml")).split("\n")
    стратегия = абзацы[абзацы.index("Стратегия ответа на замечания") + 1:]
    assert абзацы.count(П7_Р026) == 1, "в 03 нет п. 7 в редакции Р-026 §1.5"
    assert стратегия[6] == П7_Р026, f"п. 7 «Стратегии» в 03: «{стратегия[6]}»"


def test_p4_предпросмотр_читается_из_выданных_документов() -> None:
    """Предпросмотр страницы P4 собран из файлов, которые уходят покупателю,
    и совпадает с тем, что `build_preview` построил бы сейчас."""
    страница = ROOT / "products" / P4_СТРАНИЦА
    новая, _ = build_preview.render(страница, build_preview.catalog())
    assert новая == страница.read_text(encoding="utf-8"), (
        "предпросмотр P4 разошёлся с документами: python3 tools/build_preview.py --write")
    архив = архив_p4()
    for кусок in build_preview.fragments(P4):
        assert кусок["file"] in архив, кусок["file"]
        текст = части(архив[кусок["file"]])["word/document.xml"]
        for поле in ("title", "body"):
            assert нормализовать(кусок[поле].rstrip("…")) in текст, (кусок["file"], поле)


def main() -> int:
    провал = 0
    проверки = [(n, f) for n, f in sorted(globals().items())
                if n.startswith("test_") and n != "test_p4_документ_без_baseline_фраз"]
    проверки += [(f"baseline[{имя}]", functools.partial(проверить_baseline, имя))
                 for имя in BASELINE if имя not in STOP]
    for имя, проверка in проверки:
        try:
            проверка()
        except AssertionError as ошибка:
            провал += 1
            print(f"ПРОВАЛ  {имя}\n{ошибка}")
        else:
            print(f"ок  {имя}")
    return 1 if провал else 0


if __name__ == "__main__":
    sys.exit(main())
