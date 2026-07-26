#!/usr/bin/env python3
"""Публикует отложенные посты в Telegram-канал «Маржа в бетоне».

Посты лежат в content/telegram/*.md, каждый — с шапкой:

    ---
    publish_at: 2026-07-28 10:00
    link: https://marzhavbetone.ru/articles/nekotoraya-statya.html
    utm_campaign: article-nekotoraya-statya
    ---
    <b>Заголовок</b>

    Текст поста. Ссылка подставляется на место {link}.

Публикуются только те посты, у которых publish_at уже наступил и которых
нет в content/telegram/published.json. Повторно один пост не уходит.

Запуск:
    python3 tools/post_telegram.py --dry-run   # показать, ничего не отправляя
    python3 tools/post_telegram.py             # опубликовать

Переменные окружения:
    TELEGRAM_BOT_TOKEN — токен бота от @BotFather (обязательно)
    TELEGRAM_CHAT      — канал, по умолчанию @marzhavbetone
    TELEGRAM_API       — адрес API, подменяется в тестах
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "content" / "telegram"
STATE_FILE = POSTS_DIR / "published.json"
MSK = timezone(timedelta(hours=3))
SITE = "https://marzhavbetone.ru"

# Ограничение Telegram на длину текстового сообщения
MAX_LENGTH = 4096
# Разметка, которую понимает Telegram в parse_mode=HTML
ALLOWED_TAGS = {
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre", "blockquote", "span", "tg-spoiler", "br",
}


def parse_post(path: Path) -> dict:
    """Разбирает файл поста на шапку и текст."""
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not raw.startswith("---"):
        raise ValueError(f"{path.name}: нет шапки, файл должен начинаться с ---")
    _, header, body = raw.split("---", 2)

    meta: dict[str, str] = {}
    for line in header.strip().splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path.name}: строка шапки без двоеточия — {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    if "publish_at" not in meta:
        raise ValueError(f"{path.name}: в шапке нет publish_at")
    try:
        publish_at = datetime.strptime(meta["publish_at"], "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError(
            f"{path.name}: publish_at должен быть в формате «ГГГГ-ММ-ДД ЧЧ:ММ», "
            f"получено {meta['publish_at']!r}"
        ) from exc

    text = body.strip()
    if not text:
        raise ValueError(f"{path.name}: пустой текст поста")

    # Ссылка с UTM: видно, что переход пришёл именно из Telegram
    link = meta.get("link", "").strip()
    if link:
        campaign = meta.get("utm_campaign", path.stem)
        separator = "&" if "?" in link else "?"
        tagged = (
            f"{link}{separator}utm_source=telegram&utm_medium=post"
            f"&utm_campaign={urllib.parse.quote(campaign)}"
        )
        text = text.replace("{link}", tagged) if "{link}" in text else f"{text}\n\n{tagged}"
    elif "{link}" in text:
        raise ValueError(f"{path.name}: в тексте есть {{link}}, но в шапке нет link")

    used = {tag.lower() for tag in re.findall(r"</?([a-zA-Z0-9-]+)", text)}
    unknown = used - ALLOWED_TAGS
    if unknown:
        raise ValueError(
            f"{path.name}: Telegram не понимает теги {sorted(unknown)}. "
            f"Разрешены: {', '.join(sorted(ALLOWED_TAGS))}"
        )

    if len(text) > MAX_LENGTH:
        raise ValueError(
            f"{path.name}: {len(text)} символов, Telegram принимает не больше {MAX_LENGTH}"
        )

    return {
        "name": path.name,
        "publish_at": publish_at.replace(tzinfo=MSK),
        "text": text,
        "preview": meta.get("preview", "true").lower() != "false",
    }


def load_state() -> dict:
    if STATE_FILE.is_file():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def send(token: str, chat: str, post: dict) -> dict:
    api = os.environ.get("TELEGRAM_API", "https://api.telegram.org")
    payload = json.dumps({
        "chat_id": chat,
        "text": post["text"],
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": not post["preview"]},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{api}/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            answer = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Telegram ответил {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Не удалось связаться с Telegram: {exc.reason}") from exc
    if not answer.get("ok"):
        raise RuntimeError(f"Telegram отклонил пост: {answer}")
    return answer["result"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Публикация постов в Telegram")
    parser.add_argument("--dry-run", action="store_true",
                        help="показать, что было бы опубликовано, и выйти")
    args = parser.parse_args()

    if not POSTS_DIR.is_dir():
        print(f"Папки {POSTS_DIR.relative_to(ROOT)} нет — публиковать нечего")
        return 0

    posts = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        if path.name.startswith("_") or path.name == "README.md":
            continue
        try:
            posts.append(parse_post(path))
        except ValueError as exc:
            print(f"ОШИБКА: {exc}", file=sys.stderr)
            return 1

    state = load_state()
    now = datetime.now(MSK)
    due = [p for p in posts
           if p["name"] not in state and p["publish_at"] <= now]
    waiting = [p for p in posts
               if p["name"] not in state and p["publish_at"] > now]

    print(f"Постов всего: {len(posts)}, опубликовано ранее: {len(state)}, "
          f"к публикации сейчас: {len(due)}, ждут срока: {len(waiting)}")
    for post in waiting:
        print(f"  ждёт {post['publish_at']:%d.%m.%Y %H:%M} — {post['name']}")

    if not due:
        return 0

    if args.dry_run:
        for post in due:
            print(f"\n--- {post['name']} (пробный прогон, не отправлено) ---")
            print(post["text"])
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("ОШИБКА: не задан TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1
    chat = os.environ.get("TELEGRAM_CHAT", "@marzhavbetone").strip()

    failed = False
    for post in due:
        try:
            result = send(token, chat, post)
        except RuntimeError as exc:
            print(f"ОШИБКА при публикации {post['name']}: {exc}", file=sys.stderr)
            failed = True
            continue
        state[post["name"]] = {
            "message_id": result.get("message_id"),
            "published_at": datetime.now(MSK).isoformat(timespec="seconds"),
            "chat": chat,
        }
        print(f"Опубликовано: {post['name']} → сообщение {result.get('message_id')}")
        # Сохраняем сразу после каждого поста: если следующий упадёт,
        # уже отправленные не уйдут повторно
        save_state(state)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
