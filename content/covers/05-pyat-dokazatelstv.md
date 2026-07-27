# Обложка: «Пять доказательств, которые заставят заплатить»

Заменяет `assets/pyat-dokazatelstv-vypolneniya.png` — текстовую карточку из
`build_cover.py`. Рядом с кинематографичными обложками остальных разборов
она выглядит заглушкой.

Обложка используется в двух местах: статья на сайте и материал для Дзена
`content/dzen/05-pyat-dokazatelstv.md`. Меняется один файл — меняется в
обоих.

## Идея

Статья о том, что доказательства выполнения создаются в день работы и почти
не создаются позже. Самый сильный момент — секунда перед заливкой: как
только бетон закроет арматуру, проверить объём будет нечем.

Поэтому в кадре не документы, а то, что вот-вот исчезнет.

## Промпт, вариант 1 — основной

```
Cinematic wide shot at dusk on a construction site. In the foreground, a
dense rebar cage ready for concrete pouring, wet steel catching the last
orange light. A lone worker in a hard hat, seen from behind in silhouette,
raises a phone to photograph the rebar — the phone screen is the only cold
blue light in a warm frame. Concrete pump boom overhead, tower cranes and
half-built towers on the horizon under heavy dramatic clouds. Backlit haze,
deep shadows, amber rim light. Photoreal, cinematic, film still. No text,
no readable documents, face not visible.
```

## Промпт, вариант 2 — если первый выйдет мелким и суетливым

```
Cinematic low angle shot at dusk. A wall of tied rebar fills the left half
of the frame, sharp and backlit; the right half opens onto a construction
site with tower cranes silhouetted against a burning orange sky with heavy
clouds. A single cold blue camera flash bursts from the shadow at the base
of the rebar. Dust in the air, deep contrast, amber rim light. Photoreal,
dramatic, film still. No text, no people in focus, no faces.
```

## Требования, общие для всех обложек

- Контровой свет, объект уходит в силуэт.
- Палитра тёплая закатная или холодная грозовая, третьей нет.
- Стройка на заднем плане — опознавательный знак канала.
- Лиц в кадре нет: силуэт, спина, каска.
- Никакого текста в кадре, включая вывески и документы с буквами.
- Горизонтальный кадр под обложку статьи; Дзен принимает от 480×320,
  запас нужен, поэтому не меньше 1500 px по длинной стороне.

## После генерации

Файл кладётся вместо `assets/pyat-dokazatelstv-vypolneniya.png` под тем же
именем — тогда ни статью, ни материал для Дзена править не нужно.
