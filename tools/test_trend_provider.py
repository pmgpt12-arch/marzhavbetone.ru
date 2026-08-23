#!/usr/bin/env python3
"""Размеченные случаи слоя источников: чего он делать не должен.

Зачем отдельный прогон. Слой провайдера ценен ровно тем, что отказывает
там, где источника нет. Провайдер, который на нехватку ключа возвращает
пустой список, тише — и потому опаснее: конвейер поедет дальше, а ролик
поедет без референсов.

    python3 tools/test_trend_provider.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trend_provider as tp  # noqa: E402

НАСТРОЙКИ = {
    "active": "file",
    "providers": {
        "file": {"kind": "local", "input": None},
        "scrapecreators": {
            "kind": "api",
            "base_url": "https://api.scrapecreators.com",
            "endpoints": {"search": "/v1/instagram/search"},
        },
        "captapi": {
            "kind": "api",
            "base_url": "https://api.captapi.com",
            "endpoints": {"profile_reels": "/instagram/profile/reels"},
        },
        "virale": {"kind": "ui", "programmatic_access": "not_found"},
    },
}

провалов = 0


def случай(имя: str, условие: bool, подробность: str = "") -> None:
    global провалов
    if условие:
        print(f"ок        {имя}")
    else:
        провалов += 1
        print(f"НЕ ЛОВИТ  {имя}: {подробность}")


def отказ(вызов) -> str:
    """Текст отказа или пустая строка, если отказа не было."""
    try:
        вызов()
    except tp.ProviderError as exc:
        return str(exc)
    return ""


def main() -> int:
    # 1. Источник без программного интерфейса не притворяется рабочим.
    текст = отказ(lambda: tp.provider("virale", настройки=НАСТРОЙКИ))
    случай("virale_без_api_отказывает",
           "нет программного интерфейса" in текст, f"получили {текст!r}")
    случай("virale_отказ_называет_запрет_скрейпинга",
           "Скрейпинг" in текст, f"получили {текст!r}")

    # 2. Незнакомый источник не подставляется молча.
    текст = отказ(lambda: tp.provider("тиктокмагия", настройки=НАСТРОЙКИ))
    случай("незнакомый_источник_отказывает",
           "не объявлен" in текст, f"получили {текст!r}")

    # 3. Нет ключа — отказ с именем переменной, а не пустой список.
    источник = tp.ScrapeCreatorsProvider(
        НАСТРОЙКИ["providers"]["scrapecreators"], environ={})
    текст = отказ(lambda: источник.fetch("удержание", 3))
    случай("без_ключа_отказывает",
           "SCRAPECREATORS_API_KEY" in текст, f"получили {текст!r}")

    # 4. Ответ без списка записей и без аккаунтов — отказ, а не ноль карточек,
    # и он называет ключи ответа: по ним видно, что вообще вернул источник.
    источник = tp.ScrapeCreatorsProvider(
        НАСТРОЙКИ["providers"]["scrapecreators"],
        environ={"SCRAPECREATORS_API_KEY": "k"},
        transport=lambda url, headers: {"status": "ok"})
    текст = отказ(lambda: источник.fetch("удержание", 3))
    случай("ответ_без_записей_отказывает",
           "не дал роликов" in текст and "status" in текст,
           f"получили {текст!r}")

    # 4a. Поиск отдаёт подсказку — аккаунты, а не ролики. Так отвечает живой
    # ScrapeCreators (замер 23.08.2026, прогон 32639314158): в ответе
    # users, hashtags, keywords, places. Второй шаг обязан забрать ролики
    # аккаунта, а не сдаться.
    ЖИВОЙ_ПОИСК = {"users": [{"user": {"username": "buhgalter"}}],
                   "hashtags": [], "places": [], "success": True}
    РОЛИК = {"media": {
        "code": "DXyz", "taken_at": 1787443200,
        "user": {"username": "buhgalter"},
        "play_count": 412000, "like_count": 9100, "comment_count": 640,
        "video_duration": 27.5,
        "image_versions2": {"candidates": [{"url": "https://x/t.jpg"}]},
        "video_versions": [{"url": "https://x/v.mp4"}],
    }}

    def двухшаговый(url, headers):
        return {"items": [РОЛИК]} if "user/reels" in url else ЖИВОЙ_ПОИСК

    карточка = tp.ScrapeCreatorsProvider(
        НАСТРОЙКИ["providers"]["scrapecreators"],
        environ={"SCRAPECREATORS_API_KEY": "k"},
        transport=двухшаговый).fetch("удержание", 3)[0]
    случай("поиск_ведёт_к_роликам_аккаунта",
           карточка.views == 412000 and карточка.author == "buhgalter",
           f"получили {карточка.views}, {карточка.author!r}")
    случай("вложенные_адреса_разобраны",
           карточка.thumbnail == "https://x/t.jpg"
           and карточка.video_url == "https://x/v.mp4",
           f"получили {карточка.thumbnail!r}, {карточка.video_url!r}")
    случай("эпоха_стала_датой", карточка.date == "2026-08-23",
           f"получили {карточка.date!r}")
    случай("адрес_ролика_собран",
           карточка.url == "https://www.instagram.com/reel/DXyz/",
           f"получили {карточка.url!r}")

    # 4b. Аккаунты есть, роликов не отдал никто — отказ перечисляет попытки,
    # а не молчит: иначе непонятно, какой адрес пробовали.
    def только_поиск(url, headers):
        if "user/reels" in url:
            raise tp.ProviderError("HTTP 404 Not Found: ")
        return ЖИВОЙ_ПОИСК

    текст = отказ(lambda: tp.ScrapeCreatorsProvider(
        НАСТРОЙКИ["providers"]["scrapecreators"],
        environ={"SCRAPECREATORS_API_KEY": "k"},
        transport=только_поиск).fetch("удержание", 3))
    случай("перебор_адресов_роликов_назван",
           текст.count("user/reels") >= 3 and "buhgalter" in текст,
           f"получили {текст!r}")

    # 4в. Разнообразие. Замер 23.08.2026, прогон 32639533581: без предела на
    # аккаунт первый же автор закрыл весь лимит, и пять «кандидатов»
    # оказались пятью роликами одного человека. Это не выбор механики.
    ДВА_АККАУНТА = {"users": [{"user": {"username": "yurist"}},
                              {"user": {"username": "buhgalter"}}]}

    def много_роликов(url, headers):
        if "user/reels" not in url:
            return ДВА_АККАУНТА
        имя = "yurist" if "yurist" in url else "buhgalter"
        return {"items": [dict(РОЛИК["media"], code=f"{имя}{i}",
                               user={"username": имя}) for i in range(9)]}

    собрано = tp.ScrapeCreatorsProvider(
        НАСТРОЙКИ["providers"]["scrapecreators"],
        environ={"SCRAPECREATORS_API_KEY": "k"},
        transport=много_роликов).fetch("юрист", 6)
    авторы = {к.author for к in собрано}
    случай("один_аккаунт_не_закрывает_лимит",
           len(авторы) == 2 and len(собрано) == 4,
           f"авторов {авторы}, карточек {len(собрано)}")

    # 4г. Несколько запросов через черту — разные слова находят разных
    # авторов, а одна фраза находит одного и часто мимо темы.
    спрошено: list[str] = []

    def по_запросам(url, headers):
        if "user/reels" not in url:
            спрошено.append(url)
            return {"users": []}
        return {"items": []}

    отказ(lambda: tp.ScrapeCreatorsProvider(
        НАСТРОЙКИ["providers"]["scrapecreators"],
        environ={"SCRAPECREATORS_API_KEY": "k"},
        transport=по_запросам).fetch("юрист|подряд|тендер", 6))
    случай("запросы_идут_по_очереди", len(спрошено) == 3,
           f"запросов сделано {len(спрошено)}")

    # 5. Числа провайдера доезжают до карточки без переименований руками.
    источник = tp.ScrapeCreatorsProvider(
        НАСТРОЙКИ["providers"]["scrapecreators"],
        environ={"SCRAPECREATORS_API_KEY": "k"},
        transport=lambda url, headers: {"items": [{
            "id": "abc", "url": "https://instagram.com/reel/abc",
            "username": "buhgalter", "play_count": 412000,
            "like_count": 9100, "comment_count": 640,
            "video_duration": 27.5, "thumbnail_url": "https://x/t.jpg",
        }]})
    карточки = источник.fetch("удержание", 3)
    случай("измеренное_доезжает",
           карточки[0].views == 412000 and карточки[0].duration_sec == 27.5,
           f"получили {карточки[0].views}, {карточки[0].duration_sec}")

    # 6. Ключ не уезжает в адрес запроса: он живёт в заголовке.
    следы: list[tuple[str, dict]] = []

    def перехват(url, headers):
        следы.append((url, headers))
        return {"items": []}

    tp.ScrapeCreatorsProvider(
        НАСТРОЙКИ["providers"]["scrapecreators"],
        environ={"SCRAPECREATORS_API_KEY": "секрет"},
        transport=перехват).fetch("удержание", 3)
    случай("ключ_не_в_адресе", "секрет" not in следы[0][0], следы[0][0])

    # 7. Captapi называет поля иначе, и это единственное его отличие.
    источник = tp.CaptapiProvider(
        НАСТРОЙКИ["providers"]["captapi"],
        environ={"CAPTAPI_API_KEY": "k"},
        transport=lambda url, headers: {"data": [{
            "code": "xyz", "link": "https://instagram.com/reel/xyz",
            "playCount": 88000, "likeCount": 3300, "commentCount": 210,
            "duration": 19, "thumbnailUrl": "https://x/y.jpg",
        }]})
    карточка = источник.fetch("", 1)[0]
    случай("captapi_поля_разобраны",
           карточка.views == 88000 and карточка.id == "xyz",
           f"получили {карточка.views}, {карточка.id}")

    # 8. Поля суждения провайдер не заполняет — и говорит об этом.
    случай("суждение_остаётся_пустым",
           set(карточка.чего_не_хватает()) == set(tp.СУЖДЕНИЕ),
           f"пусты: {карточка.чего_не_хватает()}")

    # 9. Выгрузка владельца читается без сети и без ключа.
    with tempfile.TemporaryDirectory() as каталог:
        путь = Path(каталог) / "export.json"
        путь.write_text(json.dumps([{
            "id": "r1", "url": "https://instagram.com/reel/r1",
            "author": "yurist", "date": "2026-08-20",
            "play_count": 250000, "like_count": 7000, "comment_count": 900,
            "duration": 22, "чужое_поле": "сохранить",
        }], ensure_ascii=False), encoding="utf-8")
        карточки = tp.FileProvider(Path(каталог)).fetch("", 5)
        случай("выгрузка_читается",
               карточки[0].views == 250000 and карточки[0].author == "yurist",
               f"получили {карточки[0]}")
        случай("незнакомое_поле_не_теряется",
               карточки[0].raw.get("чужое_поле") == "сохранить",
               f"raw: {карточки[0].raw}")

    # 10. Неполная выгрузка называется неполной, а не дополняется догадкой.
    with tempfile.TemporaryDirectory() as каталог:
        (Path(каталог) / "e.json").write_text(
            json.dumps([{"id": "r2", "play_count": 10}]), encoding="utf-8")
        карточка = tp.FileProvider(Path(каталог)).fetch("", 1)[0]
        случай("неполный_замер_назван",
               "url" in карточка.дефекты_замера(),
               f"дефекты: {карточка.дефекты_замера()}")

    print(f"\nСлучаев: 21, не поймано: {провалов}")
    return 1 if провалов else 0


if __name__ == "__main__":
    sys.exit(main())
