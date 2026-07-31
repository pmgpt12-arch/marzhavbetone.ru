# Обложка: строительный мусор в смете

Заменяет `assets/stroitelnyy-musor-v-smete.png` — текстовую карточку из
`build_cover.py`.

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Гора, выросшая из одной строки

## Готовый промт

```
Wide cinematic film still at dusk on a construction site. A single narrow
skip container stands in the middle distance, correctly sized and tidy,
almost token. Directly behind and above it rises an enormous mountain of
construction debris — broken concrete with reinforcement whiskers, shattered
brick, twisted ductwork, splintered timber, torn insulation — spilling
forward past the skip and filling the entire upper half of the frame, so
that the container reads as a thimble under an avalanche. In the immediate
foreground, a lone worker in a hard hat and dirty jacket, seen from behind
in silhouette, pushes a single wheelbarrow toward the skip. Tower cranes
and half-built floors behind in volumetric haze under a burning amber sky
with heavy clouds. Strong backlight over the debris mountain, deep
blue-grey shadows across the foreground, dust hanging in the beams.
Textures of fractured concrete, rusted rebar ends, crushed brick, wet mud,
torn polyethylene, splintered wood. Atmosphere of a quantity that was
agreed small and arrived large. No readable text, no logos, no watermarks,
no visible face, photorealistic, cinematic film still, high detail.
```

## Смысловая метафора

Строка на вывоз отходов почти всегда занижена, а объём определяется не
сметой, а тем, что реально образовалось. Кадр показывает не мусор, а
разрыв между согласованной ёмкостью и настоящей горой — и человека,
который возит её своими силами.

---

## Запасная концепция

Если основной кадр выйдет слишком похожим на репортаж со свалки —
генератор любит уводить сцену в промышленный полигон, и связь со стройкой
теряется.

**Название концепции:** Счётчик, который крутится не в ту сторону

```
Wide cinematic film still at dusk at a site gate. A heavy weighbridge
platform occupies the foreground, its steel deck wet and scarred, with a
loaded dump truck standing on it seen from behind. The truck's raised body
is overflowing, debris cascading off both sides onto the deck and beyond
the platform edge, far past what the bridge could measure. A lone worker in
a hard hat, seen from behind in silhouette, stands beside the platform with
his hands at his sides, watching the spill. Tower cranes and unfinished
towers behind in volumetric haze, burning amber sky. Strong backlight
behind the truck, long shadows across the weighbridge, dust in the beams.
Textures of rusted steel plate, broken concrete, mud, exhaust haze.
Atmosphere of an overflow nobody is counting. No readable text, no logos,
no watermarks, no visible face, photorealistic, cinematic film still, high
detail.
```

Читается как «учёт есть, но он не про этот объём». Брать, если первый
вариант не сработает.

---

## После генерации

Файл кладётся в `assets/` под именем `stroitelnyy-musor-v-smete.png` —
ссылки на него уже стоят. Проверить: букв в кадре нет, лицо не видно,
палитра совпадает с соседними обложками. Табло весов в запасном варианте
не должно показывать читаемых цифр.
