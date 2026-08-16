#!/usr/bin/env python3
"""Публикация ролика или картинки в Instagram через Graph API.

ПОЧЕМУ НЕ ИЗ СЕССИИ. Замер 16.08.2026 из облачной сессии:

    curl -sS -o /dev/null -w '%{http_code}' https://graph.facebook.com  → 000
    curl -sS -o /dev/null -w '%{http_code}' https://www.instagram.com   → 000

Оба адреса закрыты прокси сессии, поэтому публикация живёт в прогоне
Actions, у которого выход в сеть свой. Это тот же порядок, что у съёмки
фрагментов (footage.yml) и у отправки в Телеграм.

ПОЧЕМУ ССЫЛКА, А НЕ ФАЙЛ. Graph API не принимает загрузку тела ролика от
клиента: он забирает файл сам по `video_url`, и адрес должен быть публично
доступен. Отсюда порядок — сначала ролик выкладывается на сайт, потом его
адрес отдаётся сюда. Приватная ссылка или файл на раннере не годятся:
проверить это можно только настоящей публикацией, поэтому режим `--probe`
существует отдельно.

ПОЧЕМУ ОЖИДАНИЕ ОБЯЗАТЕЛЬНО. Контейнер ролика собирается на стороне Meta
асинхронно: сразу после создания он в статусе IN_PROGRESS, и публикация
такого контейнера отвечает ошибкой. Поэтому между созданием и публикацией
стоит опрос статуса, а не пауза наугад.

    # проверить доступ и токен, ничего не публикуя
    python3 tools/instagram_publish.py --probe

    # опубликовать ролик
    python3 tools/instagram_publish.py --reel https://marzhavbetone.ru/media/reel-01.mp4 \
        --caption-file content/reels/captions/01.txt
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ВЕРСИЯ = "v21.0"
БАЗА = f"https://graph.facebook.com/{ВЕРСИЯ}"
# Сборка ролика на стороне Meta занимает десятки секунд; предел взят с
# запасом, чтобы прогон падал по своей причине, а не по нетерпению.
ЖДАТЬ_СЕКУНД = 300
ШАГ_ОПРОСА = 10


def запрос(адрес: str, данные: dict | None = None) -> dict:
    if данные is None:
        тело, метод = None, "GET"
    else:
        тело, метод = urllib.parse.urlencode(данные).encode(), "POST"
    попытка = urllib.request.Request(адрес, data=тело, method=метод)
    try:
        with urllib.request.urlopen(попытка, timeout=120) as ответ:
            return json.loads(ответ.read())
    except urllib.error.HTTPError as ошибка:
        текст = ошибка.read().decode(errors="replace")
        raise SystemExit(f"Graph API {ошибка.code}: {текст}") from ошибка
    except urllib.error.URLError as ошибка:
        raise SystemExit(f"сеть недоступна: {ошибка.reason}") from ошибка


def токен_и_счёт() -> tuple[str, str]:
    токен = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    счёт = os.environ.get("IG_USER_ID", "").strip()
    if not токен or not счёт:
        raise SystemExit(
            "нет IG_ACCESS_TOKEN или IG_USER_ID. Порядок их получения — "
            "docs/INSTAGRAM_SETUP.md; в прогоне они приходят из секретов")
    return токен, счёт


def проба(токен: str, счёт: str) -> int:
    """Доступ, срок жизни токена и права — без единой публикации."""
    данные = запрос(f"{БАЗА}/{счёт}?fields=username,followers_count,"
                    f"media_count&access_token={urllib.parse.quote(токен)}")
    print(f"аккаунт: @{данные.get('username')}")
    print(f"подписчиков: {данные.get('followers_count')}, "
          f"публикаций: {данные.get('media_count')}")

    # Отдельный вызов: аккаунт может отвечать, а срок токена — истекать
    # через сутки, и узнать это лучше не в момент публикации.
    debug = запрос(f"{БАЗА}/debug_token?input_token="
                   f"{urllib.parse.quote(токен)}"
                   f"&access_token={urllib.parse.quote(токен)}")
    сведения = debug.get("data", {})
    истекает = сведения.get("expires_at")
    права = сведения.get("scopes", [])
    print(f"токен действителен: {сведения.get('is_valid')}")
    print("истекает: " + ("никогда" if истекает in (0, None)
                          else time.strftime("%Y-%m-%d %H:%M",
                                             time.gmtime(истекает))))
    print(f"права: {', '.join(права) if права else 'не названы'}")

    нужное = "instagram_content_publish"
    if права and нужное not in права:
        print(f"ОШИБКА: нет права {нужное} — публикация откажет",
              file=sys.stderr)
        return 1
    return 0


def дождаться(контейнер: str, токен: str) -> None:
    предел = time.monotonic() + ЖДАТЬ_СЕКУНД
    while time.monotonic() < предел:
        состояние = запрос(f"{БАЗА}/{контейнер}?fields=status_code,status"
                           f"&access_token={urllib.parse.quote(токен)}")
        код = состояние.get("status_code")
        if код == "FINISHED":
            return
        if код == "ERROR":
            raise SystemExit(f"Meta не собрала контейнер: {состояние}")
        print(f"  контейнер {код}, ждём…")
        time.sleep(ШАГ_ОПРОСА)
    raise SystemExit(f"контейнер не собрался за {ЖДАТЬ_СЕКУНД} с")


def опубликовать(токен: str, счёт: str, ссылка: str, подпись: str,
                 вид: str) -> int:
    поля = {"access_token": токен, "caption": подпись}
    if вид == "reel":
        поля["media_type"] = "REELS"
        поля["video_url"] = ссылка
    else:
        поля["image_url"] = ссылка

    создано = запрос(f"{БАЗА}/{счёт}/media", поля)
    контейнер = создано.get("id")
    if not контейнер:
        raise SystemExit(f"контейнер не создан: {создано}")
    print(f"контейнер: {контейнер}")

    if вид == "reel":
        дождаться(контейнер, токен)

    готово = запрос(f"{БАЗА}/{счёт}/media_publish",
                    {"access_token": токен, "creation_id": контейнер})
    номер = готово.get("id")
    if not номер:
        raise SystemExit(f"публикация не прошла: {готово}")

    # Подтверждение отдельным чтением: ответ на публикацию говорит, что
    # запрос принят, а не что запись видна в аккаунте.
    запись = запрос(f"{БАЗА}/{номер}?fields=permalink,media_type,timestamp"
                    f"&access_token={urllib.parse.quote(токен)}")
    print(f"ОПУБЛИКОВАНО id={номер}")
    print(f"адрес: {запись.get('permalink')}")
    print(f"тип: {запись.get('media_type')}, время: {запись.get('timestamp')}")
    return 0


def main() -> int:
    разбор = argparse.ArgumentParser(description=__doc__)
    разбор.add_argument("--probe", action="store_true",
                        help="проверить доступ и токен, не публикуя")
    разбор.add_argument("--reel", metavar="URL", help="публичный адрес mp4")
    разбор.add_argument("--image", metavar="URL", help="публичный адрес jpg")
    разбор.add_argument("--caption-file", help="файл с подписью")
    разбор.add_argument("--caption", help="подпись строкой")
    аргументы = разбор.parse_args()

    токен, счёт = токен_и_счёт()

    if аргументы.probe:
        return проба(токен, счёт)

    if bool(аргументы.reel) == bool(аргументы.image):
        print("ОШИБКА: нужен ровно один из --reel или --image",
              file=sys.stderr)
        return 2

    if аргументы.caption_file:
        подпись = open(аргументы.caption_file, encoding="utf-8").read().strip()
    elif аргументы.caption:
        подпись = аргументы.caption
    else:
        print("ОШИБКА: нет подписи — --caption или --caption-file",
              file=sys.stderr)
        return 2

    ссылка = аргументы.reel or аргументы.image
    вид = "reel" if аргументы.reel else "image"
    return опубликовать(токен, счёт, ссылка, подпись, вид)


if __name__ == "__main__":
    raise SystemExit(main())
