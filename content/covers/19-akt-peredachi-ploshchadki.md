# Обложка: акт передачи строительной площадки

Обложки у разбора пока нет вовсе — в статье блок изображения не подключён,
в списке разборов карточка идёт на `assets/hero.jpg`. После генерации файл
кладётся как `assets/akt-peredachi-stroitelnoy-ploshchadki-obrazec.jpg`, и
тогда правятся два места: `<img class="article-cover">` в статье, `og:image`
и поле `image` в JSON-LD — их там сейчас нет, потому что ссылка на
несуществующий файл в превью хуже отсутствия картинки.

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Участок, который вам отдали таким

## Готовый промт

```
Wide cinematic film still at dawn on a construction site. In the foreground,
an empty concrete slab floor stretches away, littered with someone else's
leftovers: broken formwork panels, a coil of cut cable, a heap of rubble, a
puddle of standing water reflecting a cold sky. A single line of orange
plastic barrier tape runs across the middle of the frame from edge to edge,
dividing the slab into two halves that look identical. A lone worker in a
hard hat stands just behind the tape, seen from behind in silhouette, hands
at his sides, not yet stepping over. Beyond him, unfinished concrete floors
and tower cranes recede into volumetric haze under a cold grey-blue sky with
heavy clouds. Strong low backlight from behind the cranes, long shadows
across the debris in the foreground, dust suspended in the light. Textures of
raw concrete, splintered plywood, rusted rebar ends, mud, wet dust.
Atmosphere of a boundary that nobody wrote down. No readable text, no logos,
no watermarks, no visible face, photorealistic, cinematic film still, high
detail.
```

## Смысловая метафора

Спор о переданной площадке всегда об одном: где проходила граница и в каком
состоянии участок был до вас. Лента делит кадр на две неотличимые половины —
именно поэтому граница и состояние существуют только записанными.

---

## Запасная концепция

Если основной кадр выйдет слишком чистым — генератор любит превращать мусор в
аккуратный производственный натюрморт, и ощущение чужого следа пропадает.

**Название концепции:** Ключ без описи

```
Wide cinematic film still at dawn at the gate of a construction site. In the
foreground, an open padlock hangs from a chain-link gate, the gate pushed
half open into the frame; behind it, churned mud and tyre ruts lead away
toward unfinished concrete floors. A lone worker in a hard hat and dirty
jacket stands in the gap of the gate, seen from behind in silhouette, one
hand still on the metal. Tower cranes and scaffolding recede into volumetric
haze under a cold grey-blue sky. Strong low backlight through the gate mesh,
long shadows in the mud, dust and morning moisture in the beams. Textures of
galvanised mesh, wet clay, rusted steel, raw concrete. Atmosphere of taking
over something without an inventory. No readable text, no logos, no
watermarks, no visible face, photorealistic, cinematic film still, high
detail.
```

Читается как «вход без приёмки»: ближе к моменту допуска, дальше от спора о
состоянии. Брать, если первый вариант не сработает.

---

## После генерации

Файл кладётся в `assets/` под именем
`akt-peredachi-stroitelnoy-ploshchadki-obrazec.jpg`. Проверить: букв в кадре
нет, лицо не видно, палитра совпадает с соседними обложками, горизонтальный
кадр от 1500 px по длинной стороне.
