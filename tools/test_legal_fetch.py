#!/usr/bin/env python3
"""Поведение добытчика в сети: общий ответ, таймаут, повтор. Сети не требует.

Сеть подменяется — обращения считаются. Проверяется не разбор (он в
`test_legal_extract.py` и `test_legal_pdf.py`), а то, сколько раз
инструмент ходит наружу и что делает с отказом.

Причина замером 16.08.2026: три нормы АПК стоят на одном акте, и таймаут
по нему повторился трижды по пять попыток. Пятнадцать ожиданий вместо
пяти — на медленном хосте это разница между «прогон закончился» и «прогон
висит».
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_legal_evidence as F  # noqa: E402

АПК_ТЕЛО = (
    "Арбитражный процессуальный кодекс Российской Федерации от 24.07.2002 "
    "№ 95-ФЗ. Текст документа. "
    "Статья 4. Право на обращение в арбитражный суд. 5. Спор, возникающий из "
    "гражданских правоотношений, может быть передан на разрешение "
    "арбитражного суда после принятия сторонами мер по досудебному "
    "урегулированию по истечении тридцати календарных дней со дня "
    "направления претензии, если иные срок и порядок не установлены законом. "
    "Статья 125. Форма и содержание искового заявления. Исковое заявление "
    "подается в арбитражный суд в письменной форме и подписывается истцом "
    "или его представителем, с указанием сведений о соблюдении досудебного "
    "порядка. "
    "Статья 126. Документы, прилагаемые к исковому заявлению. К исковому "
    "заявлению прилагаются уведомление о вручении или иные документы, "
    "подтверждающие направление копий искового заявления другим лицам. "
    "Статья 128. Оставление искового заявления без движения. Арбитражный суд "
    "выносит определение об оставлении заявления без движения, если при "
    "рассмотрении вопроса о принятии установит, что оно подано с нарушением "
    "требований статей 125 и 126 настоящего Кодекса. "
    "Статья 148. Оставление заявления без рассмотрения. Арбитражный суд "
    "оставляет исковое заявление без рассмотрения, если после его принятия "
    "установит, что истцом не соблюден претензионный порядок урегулирования "
    "спора с ответчиком. "
    "Статья 149. Последствия оставления заявления без рассмотрения. ")

СТРАНИЦА = ("<html><head><title>Арбитражный процессуальный кодекс Российской "
            "Федерации</title></head><body><p>" + АПК_ТЕЛО
            + "</p></body></html>").encode("cp1251")

АПК = [{"norm_id": "apk-4-5", "act": "АПК РФ", "article": "ч. 5 ст. 4"},
       {"norm_id": "apk-125-126", "act": "АПК РФ", "article": "125, 126"},
       {"norm_id": "apk-128-148", "act": "АПК РФ", "article": "128, 148"}]
АДРЕС = "https://pravo.gov.ru/proxy/ips/?docbody=&nd=102079219"
for n in АПК:
    n["official_source"] = АДРЕС
    n["document_match"] = ["арбитражный процессуальный кодекс"]


class _Ответ:
    status = 200

    def __init__(self, payload: bytes, url: str):
        self._payload, self._url = payload, url
        self.headers = _Заголовки()

    def read(self):
        return self._payload

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Заголовки(dict):
    def get_content_charset(self):
        return None

    def get(self, key, default=""):
        return "text/html" if key == "Content-Type" else default


def _подменить(поведение):
    """Заменить сеть на заданное поведение и обнулить память прогона."""
    F._CACHE.clear()
    F._FAILED.clear()
    F._LAST_CALL[0] = 0.0
    F._SINK[0] = None
    F.POLITE_PAUSE = 0
    F.BACKOFF = (0,)
    счётчик = {"вызовов": 0}

    def fake(req, timeout=None):
        счётчик["вызовов"] += 1
        return поведение(счётчик["вызовов"], req.full_url)

    urllib.request.urlopen = fake
    return счётчик


_настоящий = urllib.request.urlopen


def test_три_нормы_апк_берут_один_ответ():
    """Один акт — одно обращение, а не три: акт общий на три нормы."""
    счёт = _подменить(lambda n, url: _Ответ(СТРАНИЦА, url))
    try:
        итог = [F.collect(norm, False, None) for norm in АПК]
    finally:
        urllib.request.urlopen = _настоящий
    assert счёт["вызовов"] == 1, f"обращений {счёт['вызовов']}, ждали 1"
    for (text, klass, _, _), norm in zip(итог, АПК):
        assert klass == F.OFFICIAL, f"{norm['norm_id']}: {klass}"
        assert text, norm["norm_id"]
    assert "тридцати календарных дней" in итог[0][0]
    assert "125" in итог[1][0] and "126" in итог[1][0]
    assert "без движения" in итог[2][0] and "без рассмотрения" in итог[2][0]


def test_из_одного_ответа_берутся_все_пять_статей():
    счёт = _подменить(lambda n, url: _Ответ(СТРАНИЦА, url))
    try:
        собрано = " ".join(F.collect(norm, False, None)[0] for norm in АПК)
    finally:
        urllib.request.urlopen = _настоящий
    for номер in ("4", "125", "126", "128", "148"):
        assert f"Статья {номер}." in собрано, f"нет статьи {номер}"
    assert счёт["вызовов"] == 1


def test_таймаут_остаётся_not_verified():
    """Недоступный источник вторичным не подменяется — молча тем более."""
    def всегда_таймаут(n, url):
        raise TimeoutError("[WinError 10060] попытка соединения не удалась")

    счёт = _подменить(всегда_таймаут)
    try:
        text, klass, _, note = F.collect(АПК[0], False, None)
    finally:
        urllib.request.urlopen = _настоящий
    assert klass == F.NOT_VERIFIED and not text
    assert "недоступен" in note, note
    assert f"попыток {F.RETRIES}" in note, note


def test_исчерпанный_адрес_не_перебирается_каждой_нормой():
    """Пятнадцать ожиданий вместо пяти — то, что чинит память отказа."""
    def всегда_таймаут(n, url):
        raise TimeoutError("[WinError 10060]")

    счёт = _подменить(всегда_таймаут)
    try:
        for norm in АПК:
            F.collect(norm, False, None)
    finally:
        urllib.request.urlopen = _настоящий
    assert счёт["вызовов"] == F.RETRIES, \
        f"обращений {счёт['вызовов']}, ждали {F.RETRIES} на все три нормы"


def test_повтор_после_переходного_таймаута_даёт_успех():
    def дважды_мимо(n, url):
        if n <= 2:
            raise TimeoutError("[WinError 10060]")
        return _Ответ(СТРАНИЦА, url)

    счёт = _подменить(дважды_мимо)
    try:
        text, klass, _, _ = F.collect(АПК[1], False, None)
    finally:
        urllib.request.urlopen = _настоящий
    assert klass == F.OFFICIAL, klass
    assert "Статья 125." in text and "Статья 126." in text
    assert счёт["вызовов"] == 3


def test_код_ответа_повтора_не_получает():
    """HTTP-код — это ответ, а не молчание: повторять нечего."""
    def отказ(n, url):
        raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)

    счёт = _подменить(отказ)
    try:
        _, klass, _, note = F.collect(АПК[0], False, None)
    finally:
        urllib.request.urlopen = _настоящий
    assert klass == F.NOT_VERIFIED
    assert "код 403" in note, note
    assert счёт["вызовов"] == 1, f"обращений {счёт['вызовов']}, ждали 1"



def test_второй_заход_поднимает_упавшее_на_транспорте():
    """Хост, молчавший в начале прогона, к концу часто отвечает.

    Проверяется через `main`: первый круг по трём нормам АПК кладётся в
    таймаут, второй отвечает. Итог — official, а не ещё один заход
    владельца.
    """
    import io
    import contextlib
    состояние = {"молчит": True}

    def сначала_молчит(n, url):
        if состояние["молчит"]:
            raise TimeoutError("[WinError 10060]")
        return _Ответ(СТРАНИЦА, url)

    счёт = _подменить(сначала_молчит)
    # Паузу второго круга делаем узнаваемой: задержки повторов тоже нулевые,
    # и по нулю их не отличить.
    F.RETRY_ROUND_PAUSE = 7
    исходный_norms = F.NORMS
    записано = []
    F.write = lambda norm_id, **kw: записано.append(norm_id)
    F.yaml.safe_load = lambda text: {"norms": АПК}

    def оживить():
        состояние["молчит"] = False
    старый_sleep = F.time.sleep
    F.time.sleep = lambda s: оживить() if s == F.RETRY_ROUND_PAUSE else None

    try:
        with contextlib.redirect_stdout(io.StringIO()) as вывод:
            F.sys.argv = ["fetch", "--all"]
            код = F.main()
    finally:
        urllib.request.urlopen = _настоящий
        F.time.sleep = старый_sleep
        F.NORMS = исходный_norms
    текст = вывод.getvalue()
    assert "Второй заход" in текст, текст[-300:]
    assert "official 3" in текст, текст[-300:]
    assert код == 0, код
    assert sorted(записано) == ["apk-125-126", "apk-128-148", "apk-4-5"], записано


def test_второй_заход_не_прячет_полный_отказ():
    """Молчит и во второй раз — NOT_VERIFIED, а не тихий пропуск."""
    import io
    import contextlib

    def всегда_молчит(n, url):
        raise TimeoutError("[WinError 10060]")

    _подменить(всегда_молчит)
    F.RETRY_ROUND_PAUSE = 0
    записано = []
    F.write = lambda norm_id, **kw: записано.append(norm_id)
    F.yaml.safe_load = lambda text: {"norms": АПК}
    старый_sleep = F.time.sleep
    F.time.sleep = lambda s: None
    try:
        with contextlib.redirect_stdout(io.StringIO()) as вывод:
            F.sys.argv = ["fetch", "--all"]
            код = F.main()
    finally:
        urllib.request.urlopen = _настоящий
        F.time.sleep = старый_sleep
    текст = вывод.getvalue()
    assert "not_verified 3" in текст, текст[-300:]
    assert код == 1, код
    assert записано == [], записано


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
        else:
            print(f"  ✓ {t.__name__}")
    print(f"\nПроверок {len(tests)}, упало {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
