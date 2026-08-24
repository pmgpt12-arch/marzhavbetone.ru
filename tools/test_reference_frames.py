#!/usr/bin/env python3
"""Размеченные случаи вырезки кадров: сеть и ffmpeg подменены.

Зачем. Инструмент ходит наружу и запускает чужую программу, поэтому в
проверке нет ни того ни другого — подменяются оба. Проверяется решение, а
не ffmpeg: где гуще кадры, что делать без адреса, как звучит отказ.

    python3 tools/test_reference_frames.py
"""
from __future__ import annotations

import sys
import tempfile
import urllib.error
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_frames as кадры  # noqa: E402

провалов = 0


def случай(имя: str, условие: bool, подробность: str = "") -> None:
    global провалов
    if условие:
        print(f"ок        {имя}")
    else:
        провалов += 1
        print(f"НЕ ЛОВИТ  {имя}: {подробность}")


class ОтветЗаглушка:
    def __init__(self, тело: bytes = b"video"):
        self.тело = тело

    def read(self, *_):
        тело, self.тело = self.тело, b""
        return тело

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class Итог:
    def __init__(self, код: int):
        self.returncode = код


def карточка(каталог: Path, **поля) -> Path:
    данные = {"id": "REEL1", "video_url": "https://x/v.mp4",
              "duration_sec": 12.0, **поля}
    путь = каталог / "card.yaml"
    путь.write_text(yaml.safe_dump(данные, allow_unicode=True), encoding="utf-8")
    return путь


def main() -> int:
    # 1. Первые секунды разбираются плотнее: там зритель и уходит.
    точки = кадры.отметки(12.0)
    начало = [t for t in точки if t <= 3.0]
    случай("начало_плотнее_хвоста", len(начало) >= 6 and точки[1] - точки[0] == 0.5,
           f"точки: {точки}")

    # 2. Короткий ролик не даёт отметок за своим концом.
    случай("не_режем_за_концом", all(t < 4.0 for t in кадры.отметки(4.0)),
           f"точки: {кадры.отметки(4.0)}")

    # 3. Совсем короткий всё равно даёт хотя бы один кадр.
    случай("нулевая_длительность_даёт_кадр", кадры.отметки(0.0) == [0.0],
           f"точки: {кадры.отметки(0.0)}")

    with tempfile.TemporaryDirectory() as временный:
        корень = Path(временный)
        прежний = кадры.КАДРЫ
        кадры.КАДРЫ = корень / "frames"
        try:
            # 4. Кадры складываются по идентификатору ролика, подпись рядом.
            путь = карточка(корень, raw={"media": {"caption": {"text": "Текст подписи"}}})

            def ffmpeg(команда):
                Path(команда[-1]).write_bytes(b"jpg")
                return Итог(0)

            строка, число = кадры.обработать(
                путь, opener=lambda *a, **k: ОтветЗаглушка(), runner=ffmpeg)
            случай("кадры_вырезаны", число >= 6, строка)
            случай("подпись_сохранена",
                   (кадры.КАДРЫ / "REEL1" / "caption.txt").exists(), строка)

            # 5. Повторный заход не переснимает готовое.
            строка, число = кадры.обработать(
                путь, opener=lambda *a, **k: ОтветЗаглушка(), runner=ffmpeg)
            случай("готовое_не_переснимается", число == 0 and "уже есть" in строка,
                   строка)

            # 6. Протухшая ссылка объясняется словами, а не кодом.
            def просрочено(*a, **k):
                raise urllib.error.HTTPError("https://x/v.mp4", 403, "Forbidden", {}, None)

            путь2 = карточка(корень, id="REEL2")
            try:
                кадры.обработать(путь2, opener=просрочено, runner=ffmpeg)
                текст = ""
            except кадры.FramesError as exc:
                текст = str(exc)
            случай("протухшая_ссылка_названа",
                   "403" in текст and "пересобрать" in текст, f"получили {текст!r}")

            # 7. Нет адреса — не отказ, а строка о том, что взять неоткуда.
            путь3 = карточка(корень, id="REEL3", video_url="")
            строка, число = кадры.обработать(путь3, runner=ffmpeg)
            случай("без_адреса_говорим_прямо",
                   число == 0 and "нет video_url" in строка, строка)

            # 8. ffmpeg не отдал ни кадра — это отказ, а не тихий ноль.
            путь4 = карточка(корень, id="REEL4")
            try:
                кадры.обработать(путь4, opener=lambda *a, **k: ОтветЗаглушка(),
                                 runner=lambda команда: Итог(1))
                текст = ""
            except кадры.FramesError as exc:
                текст = str(exc)
            случай("пустая_вырезка_это_отказ", "ни одного кадра" in текст,
                   f"получили {текст!r}")
        finally:
            кадры.КАДРЫ = прежний

    # 10. Добыча ffmpeg колесом: pip и права администратора не нужны.
    # Проверяется решение, а не сеть — каталог PyPI и само колесо подменены.
    import io, json as _json, zipfile

    буфер = io.BytesIO()
    with zipfile.ZipFile(буфер, "w") as zf:
        zf.writestr("imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0", b"BINARY")
    колесо = буфер.getvalue()

    class Поток:
        def __init__(self, тело):
            self.тело = тело

        def read(self, *_):
            тело, self.тело = self.тело, b""
            return тело

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def каталог_pypi(url, *a, **k):
        if url.endswith("/json"):
            return Поток(_json.dumps({"urls": [
                {"filename": "imageio_ffmpeg-0.5-py3-none-manylinux2014_x86_64.whl",
                 "url": "https://files.pythonhosted.org/w.whl"},
                {"filename": "imageio_ffmpeg-0.5.tar.gz",
                 "url": "https://files.pythonhosted.org/s.tar.gz"},
            ]}).encode())
        return Поток(колесо)

    with tempfile.TemporaryDirectory() as врем:
        прежний_кэш = кадры.КЭШ_FFMPEG
        кадры.КЭШ_FFMPEG = Path(врем) / "cache"
        try:
            путь = кадры._из_колеса(opener=каталог_pypi)
            случай("ffmpeg_добыт_колесом",
                   Path(путь).exists() and Path(путь).stat().st_mode & 0o111,
                   f"получили {путь}")
            # Повторный заход берёт уже добытое, а не качает снова.
            снова = кадры._из_колеса(opener=lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("не должно было качать заново")))
            случай("колесо_не_качается_дважды", снова == путь, снова)
        finally:
            кадры.КЭШ_FFMPEG = прежний_кэш

    print(f"\nСлучаев: 11, не поймано: {провалов}")
    return 1 if провалов else 0


if __name__ == "__main__":
    sys.exit(main())
