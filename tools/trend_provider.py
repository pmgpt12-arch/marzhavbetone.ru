#!/usr/bin/env python3
"""Слой источника референсов: один вход, сменный провайдер.

ЗАЧЕМ. Ролик, написанный без разобранного чужого ролика, — угадывание.
Требование владельца 23.08.2026: до сценария на руках 3–5 реальных роликов
с числами и с разбором механики. Чтобы смена источника не переписывала
конвейер, источник спрятан за одним интерфейсом:

    provider(name).fetch(query, limit) -> list[ReferenceCard]

ЧТО ЗДЕСЬ РАЗДЕЛЕНО И ПОЧЕМУ. Поля карточки делятся на два вида, и это
главное решение файла:

    ИЗМЕРЕННОЕ  id, source, url, date, author, duration, views, likes,
                comments, shares, thumbnail, video_url
                — приходит от провайдера. Выдумывать нечего.

    СУЖДЕНИЕ    hook_type, first_seconds, shot_rhythm, avg_beat,
                video_static_ratio, text_style, voice_style, conflict,
                curiosity_gap, escalation, payoff, cta_type, why_relevant
                — ставит человек или модель, посмотрев ролик.

Провайдер заполняет только первое и честно оставляет второе пустым. Пока
суждение не проставлено, карточка не годится в дело — это проверяет
`check_reel_refs.py`. Смешать два вида полей значило бы получить
правдоподобный разбор ролика, которого никто не смотрел.

СЕТЬ ЗДЕСЬ НЕ ОБЯЗАТЕЛЬНА. Провайдер `file` читает выгрузку владельца и
работает без ключа и без выхода наружу — это рабочий режим, а не заглушка:
из облачной сессии закрыты все провайдеры разом (замер в
`data/social/trend-providers.yaml`).

    python3 tools/trend_provider.py --list
    python3 tools/trend_provider.py --provider file --out content/reels/references/
    python3 tools/trend_provider.py --provider scrapecreators \\
        --query "гарантийное удержание подряд" --limit 5 --out <каталог>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
РЕЕСТР = ROOT / "data" / "social" / "trend-providers.yaml"
ВЫГРУЗКА = ROOT / "content" / "reels" / "references" / "inbox"

# Поля, которые обязан принести источник. Пустое здесь — дефект выгрузки
# или ответа, а не повод дописать от себя.
ИЗМЕРЕННОЕ = ("id", "source", "url", "author", "date", "duration_sec", "views")

# Поля суждения: их ставит тот, кто ролик посмотрел. Провайдер оставляет
# пустыми намеренно.
СУЖДЕНИЕ = (
    "hook_type", "first_seconds", "shot_rhythm", "avg_beat_sec",
    "video_static_ratio", "text_style", "voice_style", "conflict",
    "curiosity_gap", "escalation", "payoff", "cta_type", "why_relevant",
)

ТАЙМАУТ = 30


class ProviderError(Exception):
    """Отказ источника, о котором можно сказать словами."""


@dataclass
class ReferenceCard:
    """Карточка референса. Порядок полей — порядок разбора."""

    # измеренное. Пустая строка — не умолчание «и так сойдёт», а состояние
    # «источник этого не дал»: его называет `дефекты_замера`. Обязательное
    # поле без значения по умолчанию уронило бы разбор неполной выгрузки
    # трейсбеком вместо строки о том, чего в ней не хватает.
    id: str = ""
    source: str = ""
    url: str = ""
    author: str = ""
    date: str = ""
    duration_sec: float = 0.0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int | None = None
    thumbnail: str = ""
    video_url: str = ""
    # суждение
    hook_type: str = ""
    first_seconds: str = ""
    shot_rhythm: str = ""
    avg_beat_sec: float | None = None
    video_static_ratio: str = ""
    text_style: str = ""
    voice_style: str = ""
    conflict: str = ""
    curiosity_gap: str = ""
    escalation: str = ""
    payoff: str = ""
    cta_type: str = ""
    why_relevant: str = ""
    # служебное
    niche: str = ""
    fetched_by: str = ""
    judged_by: str = "pending"
    raw: dict = field(default_factory=dict)

    def чего_не_хватает(self) -> list[str]:
        """Пустые поля суждения. Пока список не пуст, карточка сырая."""
        пусто = []
        for имя in СУЖДЕНИЕ:
            значение = getattr(self, имя)
            if значение in ("", None):
                пусто.append(имя)
        return пусто

    def дефекты_замера(self) -> list[str]:
        """Пустые поля, которые обязан был принести источник."""
        return [имя for имя in ИЗМЕРЕННОЕ if not getattr(self, имя)]


def реестр() -> dict:
    return yaml.safe_load(РЕЕСТР.read_text(encoding="utf-8"))


def _int(значение) -> int:
    try:
        return int(значение)
    except (TypeError, ValueError):
        return 0


def _float(значение) -> float:
    try:
        return float(значение)
    except (TypeError, ValueError):
        return 0.0


def _запрос(url: str, headers: dict, transport=None) -> dict:
    """Единственное место, где ходят в сеть. В проверках подменяется."""
    if transport is not None:
        return transport(url, headers)
    запрос = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(запрос, timeout=ТАЙМАУТ) as ответ:
            return json.loads(ответ.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        тело = exc.read().decode("utf-8", "replace")[:400]
        raise ProviderError(f"HTTP {exc.code} {exc.reason}: {тело}") from exc
    except OSError as exc:
        raise ProviderError(f"{type(exc).__name__}: {exc}") from exc


def _ключ(имя_переменной: str, environ: dict | None = None) -> str:
    env = environ if environ is not None else os.environ
    ключ = str(env.get(имя_переменной, "")).strip()
    if not ключ:
        raise ProviderError(
            f"Нет ключа: переменная {имя_переменной} не задана. "
            "Секрет репозитория заводит владелец; из сессии это невыполнимо."
        )
    return ключ


class FileProvider:
    """Выгрузка владельца: JSON или YAML, положенные в каталог.

    Ключа не требует и в сеть не ходит. Формат — список записей с любыми
    из известных имён полей; неизвестные ключи сохраняются в `raw`, чтобы
    выгрузка не теряла того, чего мы ещё не разбираем.
    """

    name = "file"

    def __init__(self, каталог: Path | None = None) -> None:
        self.каталог = Path(каталог) if каталог else ВЫГРУЗКА

    def fetch(self, query: str = "", limit: int = 10, **_) -> list[ReferenceCard]:
        if not self.каталог.exists():
            raise ProviderError(
                f"Каталога выгрузки нет: {self.каталог}. "
                "Владелец кладёт сюда экспорт, дальше карточки собираются сами."
            )
        записи: list[dict] = []
        for путь in sorted(self.каталог.iterdir()):
            if путь.suffix.lower() not in (".json", ".yaml", ".yml"):
                continue
            текст = путь.read_text(encoding="utf-8")
            данные = (json.loads(текст) if путь.suffix.lower() == ".json"
                      else yaml.safe_load(текст))
            if isinstance(данные, dict):
                данные = данные.get("items") or данные.get("reels") or [данные]
            записи.extend(данные or [])
        if query:
            запрос = query.lower()
            записи = [з for з in записи
                      if запрос in json.dumps(з, ensure_ascii=False).lower()]
        return [self._карточка(з) for з in записи[:limit]]

    def _карточка(self, запись: dict) -> ReferenceCard:
        известные = {f for f in ReferenceCard.__dataclass_fields__ if f != "raw"}
        свои = {k: v for k, v in запись.items() if k in известные}
        свои.setdefault("id", str(запись.get("shortcode") or запись.get("code") or ""))
        свои.setdefault("source", "file")
        свои["views"] = _int(свои.get("views") or запись.get("play_count"))
        свои["likes"] = _int(свои.get("likes") or запись.get("like_count"))
        свои["comments"] = _int(свои.get("comments") or запись.get("comment_count"))
        свои["duration_sec"] = _float(свои.get("duration_sec") or запись.get("duration"))
        свои["fetched_by"] = "file"
        свои["raw"] = {k: v for k, v in запись.items() if k not in известные}
        return ReferenceCard(**свои)


class _HttpProvider:
    """Общая часть сетевых провайдеров: ключ, адрес, разбор ответа."""

    name = ""
    key_env = ""

    def __init__(self, настройки: dict, environ: dict | None = None,
                 transport=None) -> None:
        self.настройки = настройки
        self.environ = environ
        self.transport = transport

    def _base(self) -> str:
        return str(self.настройки.get("base_url", "")).rstrip("/")

    def _headers(self) -> dict:
        return {"x-api-key": _ключ(self.key_env, self.environ),
                "Accept": "application/json"}

    def fetch(self, query: str = "", limit: int = 10, **_) -> list[ReferenceCard]:
        адрес = self._адрес(query, limit)
        ответ = _запрос(адрес, self._headers(), self.transport)
        записи = self._записи(ответ)
        return [self._карточка(з) for з in записи[:limit]]

    def _адрес(self, query: str, limit: int) -> str:  # pragma: no cover
        raise NotImplementedError

    def _записи(self, ответ: dict) -> list[dict]:
        for ключ in ("items", "reels", "data", "results", "posts"):
            значение = ответ.get(ключ)
            if isinstance(значение, list):
                return значение
        raise ProviderError(
            f"В ответе {self.name} нет списка записей; ключи ответа: "
            f"{', '.join(sorted(ответ)) or 'нет'}"
        )


class ScrapeCreatorsProvider(_HttpProvider):
    name = "scrapecreators"
    key_env = "SCRAPECREATORS_API_KEY"

    def _адрес(self, query: str, limit: int) -> str:
        путь = self.настройки.get("endpoints", {}).get("search", "/v1/instagram/search")
        параметры = urllib.parse.urlencode({"query": query, "amount": limit})
        return f"{self._base()}{путь}?{параметры}"

    def _карточка(self, запись: dict) -> ReferenceCard:
        return ReferenceCard(
            id=str(запись.get("id") or запись.get("shortcode") or ""),
            source="scrapecreators",
            url=str(запись.get("url") or запись.get("permalink") or ""),
            author=str(запись.get("username") or запись.get("owner") or ""),
            date=str(запись.get("taken_at") or запись.get("published_at") or ""),
            duration_sec=_float(запись.get("video_duration") or запись.get("duration")),
            views=_int(запись.get("play_count") or запись.get("view_count")),
            likes=_int(запись.get("like_count")),
            comments=_int(запись.get("comment_count")),
            shares=запись.get("share_count"),
            thumbnail=str(запись.get("thumbnail_url") or запись.get("display_url") or ""),
            video_url=str(запись.get("video_url") or ""),
            fetched_by="scrapecreators",
            raw=запись,
        )


class CaptapiProvider(_HttpProvider):
    name = "captapi"
    key_env = "CAPTAPI_API_KEY"

    def _адрес(self, query: str, limit: int) -> str:
        путь = self.настройки.get("endpoints", {}).get(
            "profile_reels", "/instagram/profile/reels")
        параметры = urllib.parse.urlencode({"query": query, "limit": limit})
        return f"{self._base()}{путь}?{параметры}"

    def _карточка(self, запись: dict) -> ReferenceCard:
        return ReferenceCard(
            id=str(запись.get("id") or запись.get("code") or ""),
            source="captapi",
            url=str(запись.get("url") or запись.get("link") or ""),
            author=str(запись.get("username") or запись.get("author") or ""),
            date=str(запись.get("createdAt") or запись.get("date") or ""),
            duration_sec=_float(запись.get("duration")),
            views=_int(запись.get("playCount") or запись.get("views")),
            likes=_int(запись.get("likeCount") or запись.get("likes")),
            comments=_int(запись.get("commentCount") or запись.get("comments")),
            shares=запись.get("shareCount"),
            thumbnail=str(запись.get("thumbnailUrl") or ""),
            video_url=str(запись.get("videoUrl") or ""),
            fetched_by="captapi",
            raw=запись,
        )


ПРОВАЙДЕРЫ = {
    "file": FileProvider,
    "scrapecreators": ScrapeCreatorsProvider,
    "captapi": CaptapiProvider,
}


def provider(имя: str | None = None, *, environ=None, transport=None,
             настройки: dict | None = None):
    """Собирает провайдера по имени из реестра. Единственная точка выбора."""
    данные = настройки if настройки is not None else реестр()
    имя = имя or данные.get("active") or "file"
    объявлен = данные.get("providers", {}).get(имя)
    if объявлен is None:
        известные = ", ".join(sorted(данные.get("providers", {})))
        raise ProviderError(
            f"Провайдер {имя!r} не объявлен в {РЕЕСТР.name}; известны: {известные}. "
            "Новый источник сначала попадает в реестр с состоянием проверки."
        )
    if объявлен.get("kind") == "ui":
        raise ProviderError(
            f"У провайдера {имя!r} нет программного интерфейса "
            f"({объявлен.get('programmatic_access', 'not_found')}). "
            "Скрейпинг интерфейса браузером здесь не заводится: есть источники "
            "с объявленным API."
        )
    класс = ПРОВАЙДЕРЫ.get(имя)
    if класс is None:
        raise ProviderError(f"Провайдер {имя!r} объявлен в реестре, но не реализован")
    if класс is FileProvider:
        каталог = объявлен.get("input")
        return FileProvider(ROOT / каталог if каталог else None)
    return класс(объявлен, environ=environ, transport=transport)


def записать(карточки: list[ReferenceCard], каталог: Path) -> list[Path]:
    каталог.mkdir(parents=True, exist_ok=True)
    пути = []
    for карточка in карточки:
        имя = f"{карточка.source}-{карточка.id or 'bez-id'}.yaml".replace("/", "-")
        путь = каталог / имя
        путь.write_text(
            yaml.safe_dump(asdict(карточка), allow_unicode=True, sort_keys=False),
            encoding="utf-8")
        пути.append(путь)
    return пути


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", default=None)
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--out", default=None)
    parser.add_argument("--list", action="store_true",
                        help="показать реестр источников и состояние проверки")
    args = parser.parse_args(argv)

    данные = реестр()
    if args.list:
        print(f"Провайдер по умолчанию: {данные.get('active')}")
        for имя, п in данные.get("providers", {}).items():
            ключ = п.get("key_env") or "не нужен"
            print(f"  {имя:16} {п.get('kind','?'):6} проверен: {п.get('checked','?'):6} "
                  f"ключ: {ключ}")
        return 0

    try:
        источник = provider(args.provider, настройки=данные)
        карточки = источник.fetch(args.query, args.limit)
    except ProviderError as exc:
        print(f"Источник не дал данных: {exc}", file=sys.stderr)
        return 2

    if not карточки:
        print("Источник ответил, но записей нет — карточки не пишутся",
              file=sys.stderr)
        return 3

    for карточка in карточки:
        дефекты = карточка.дефекты_замера()
        метка = f"  НЕПОЛНО: {', '.join(дефекты)}" if дефекты else ""
        print(f"{карточка.source:15} {карточка.id:22} "
              f"{карточка.views:>9} просмотров  {карточка.url}{метка}")

    if args.out:
        пути = записать(карточки, Path(args.out))
        сырых = sum(1 for к in карточки if к.чего_не_хватает())
        print(f"\nЗаписано карточек: {len(пути)} в {args.out}")
        print(f"Ждут разбора человеком: {сырых} "
              f"(поля суждения провайдер не заполняет)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
