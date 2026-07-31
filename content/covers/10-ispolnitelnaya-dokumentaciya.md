# Обложка: исполнительная документация — состав и передача

Заменяет `assets/ispolnitelnaya-dokumentaciya-sostav.png` — текстовую
карточку из `build_cover.py`.

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Турникет, который не пропускает деньги

## Готовый промт

```
Wide cinematic film still at dusk at the boundary of a construction site.
A heavy steel turnstile-style barrier stands closed across the centre of
the frame, its bars rusted and wet, blocking a narrow passage between two
raw concrete walls. On the near side, stacked hard against the bars, a tall
unstable tower of cardboard archive boxes and bundled rolls leans under its
own weight; one bundle has slipped and lies on the ground. On the far side
of the barrier, empty lit ground stretches away toward tower cranes and
unfinished floors in volumetric haze under a burning amber sky. A lone
worker in a hard hat and dirty jacket, seen from behind in silhouette,
stands on the near side with both hands on the bars, facing the light he
cannot reach. Strong backlight through the barrier throwing hard striped
shadows back over the boxes, deep blue-grey shadow on the near side, dust
suspended in the beams. Textures of rusted steel, damp cardboard, tied
twine, raw concrete, mud. Atmosphere of payment held on the other side of
paperwork. No readable text, no logos, no watermarks, no visible face,
photorealistic, cinematic film still, high detail.
```

## Смысловая метафора

Комплект документации — не отчётность, а пропуск: пока он не собран,
оплата стоит по ту сторону, и объём выполненных работ этого не меняет.
Кадр показывает не бумаги, а границу, через которую они не пускают.

---

## Запасная концепция

Если основной кадр выйдет слишком буквальным — генератор охотно рисует
проходную с вахтёром, и смысл съезжает на охрану.

**Название концепции:** Мост, у которого не хватает пролёта

```
Wide cinematic film still at dusk. A concrete bridge deck runs from the
foreground toward the centre of the frame and stops abruptly at a gap of
several metres; the far section continues on the other side, lit warm, and
the missing span lies in shadow far below among rebar and debris. A lone
worker in a hard hat, seen from behind in silhouette, stands at the broken
edge with a heavy roll of drawings under one arm, looking across. Tower
cranes and half-built towers behind in volumetric haze, burning amber sky
with heavy clouds. Deep blue-grey shadows in the gap, strong warm rim light
on the far deck. Textures of raw concrete, exposed rusted reinforcement,
gravel dust, torn paper. Atmosphere of work that is finished on both sides
and connects nowhere. No readable text, no logos, no watermarks, no visible
face, photorealistic, cinematic film still, high detail.
```

Читается как «работа сделана, но не сдана»: шире по смыслу, слабее по
привязке к документации. Брать, если первый вариант не сработает.

---

## После генерации

Файл кладётся в `assets/` под именем
`ispolnitelnaya-dokumentaciya-sostav.png` — ссылки на него уже стоят.
Проверить: букв в кадре нет, лицо не видно, палитра совпадает с соседними
обложками.
