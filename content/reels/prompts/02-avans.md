# Промпты для ролика 2 — аванс

Сценарий: `content/reels/02-avans-kryuchok.md`. Стиль: `content/reels/style.md`.

Тайминг и текст на экран берутся из сценария и не меняются. Меняется только
то, что происходит в кадре: в сценарии это описано под съёмку — письмо на
экране телефона, строка договора крупно. Для генерации такие кадры не
годятся, потому что читаемый текст модели портят. Ниже каждый кадр
переведён в метафору, а текст ложится поверх при сборке.

## Кадр 1 (0–3 с) — обложка статьи

**Изображение генерировать не нужно.** Первым кадром берётся готовая
обложка `assets/avans-eto-ne-dengi-eto-kryuchok.png`: крюк крана, на
который насажена пачка купюр, оранжевое небо, силуэты кранов.

Стиль совпадёт гарантированно, а зритель, дойдя до сайта, увидит ту же
картинку.

**Оживление (image-to-video):**

```
The suspended hook with the banknote stack sways very slowly on its rope,
almost imperceptible pendulum motion. Thick amber dust drifts across the
frame. Distant cranes stay static. Camera slowly pushes in. Cinematic,
moody, backlit haze. No text, no people, no camera shake.
```

## Кадр 2 (3–8 с) — деньги ушли в объект

**Изображение:**

```
Cinematic wide shot at dusk on a construction site. Silhouetted excavator
and a stack of building materials in the foreground, backlit by a low
orange sun behind heavy clouds. Tower cranes on the horizon. Deep shadows,
amber rim light, dust in the air. Photoreal, dramatic, film still. No
text, no faces, no logos.
```

**Оживление:**

```
Slow parallax push forward past the materials. Dust drifts through the
sunbeams, clouds move slowly. Static machinery. No people, no text.
```

## Кадр 3 (8–13 с) — обратный отсчёт

**Изображение:**

```
Cinematic close shot of an old mechanical wall clock mounted on raw
concrete, backlit by cold grey daylight from a window opening. Rain
streaks on the concrete. Muted palette, single warm lamp glow in the
background. Photoreal, dramatic, shallow depth of field. No text, no
numbers on the dial, no people.
```

Часы без цифр — намеренно: цифры на циферблате модели рисуют
неубедительно, а нам нужен только смысл «время пошло».

**Оживление:**

```
The clock hands move quickly, several hours in a few seconds. Rain runs
down the concrete. Light dims gradually. Camera holds still. No text.
```

## Кадр 4 (13–18 с) — крюк забирает деньги

**Изображение:**

```
Cinematic low angle shot. A heavy rusted crane hook rises into a stormy
sky, lifting a bundle wrapped in canvas away from the ground. Silhouetted
half-built concrete tower on the right, tower cranes behind. Cold grey
storm light with a thin warm rim on the hook. Photoreal, dramatic. No
text, no faces.
```

**Оживление:**

```
The hook and its load rise slowly out of frame while the camera tilts up
to follow. Clouds move fast behind. Wind moves the canvas slightly. No
text, no people.
```

## Кадр 5 (18–20 с) — пустой объект

**Изображение:**

```
Cinematic wide shot of an abandoned unfinished concrete frame building at
dusk, empty and silent, puddles on bare ground reflecting a dim orange
sky. No machinery, no people. Cold desaturated palette with a single warm
horizon glow. Photoreal, bleak, film still. No text.
```

**Оживление:**

```
Very slow drone-like drift to the left, revealing more of the empty frame.
Water ripples slightly in the puddles. Clouds move. No people, no text.
```

## Кадр 6 (20–22 с) — финал

**Изображение:**

```
Cinematic close shot of a single steel rebar rod standing upright in wet
concrete, backlit by warm low sun through construction dust. Shallow depth
of field, dark background, strong orange rim light. Photoreal, minimal,
one object in frame. No text, no people.
```

**Оживление:**

```
Slow push in on the rebar, dust drifting through the backlight, subtle
lens flare. Camera steady. No text.
```

---

## Сборка

Шесть клипов по 4–6 секунд склеиваются, накладывается текст:

```bash
python3 tools/build_reel.py content/reels/02-avans-kryuchok.md \
    --footage sobrannoe-video.mp4 --out reel-02.mp4
```

Клипы генерируются без звука, поэтому дорожку нужно добавить отдельно:
голос за кадром по тексту сценария или музыка.

## Что проверить на результате

1. **Нет ли букв в кадре.** Любая надпись, вывеска или цифра — брак:
   модели пишут с ошибками, а зритель это замечает.
2. **Не «плывут» ли объекты.** Краны и здания должны оставаться на месте;
   если конструкции меняют форму, клип перегенерировать.
3. **Держится ли палитра.** Все шесть кадров должны выглядеть из одного
   ролика, а не из шести разных.
4. **Не перекрывает ли текст главный объект** — подложки ставятся по
   левому краю, крюк и техника должны остаться видны.
