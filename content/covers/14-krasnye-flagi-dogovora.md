# Обложка: красные флаги договора субподряда

Заменяет `assets/krasnye-flagi-dogovora-subpodryada.png` — текстовую
карточку из `build_cover.py`. Используется в статье на сайте и в списке
разборов: меняется один файл — меняется везде.

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Настил, в котором несколько досок лежат на пустоте

## Готовый промт

```
Wide cinematic film still at dusk, camera low and close to the deck, on a
construction site. A temporary timber walkway runs from the foreground
across a deep excavation: identical weathered planks, laid tight, uniform
in colour and wear, a handrail of rusted scaffold tube along one side.
From this low angle the trick is visible — under the middle of the run the
supporting beam stops short, and several planks in the centre of the
walkway rest on nothing at all, a black open shaft yawning beneath them,
while from above they look exactly like every other board. A lone
subcontractor in a hard hat and dirty jacket steps onto the near end of
the walkway, seen from behind in silhouette, a heavy bundle on one
shoulder, moving at working pace. Tower cranes and an unfinished concrete
frame recede into volumetric haze under a burning amber sky. Hard
backlight along the length of the walkway turning the planks into a bright
ribbon, deep blue-grey shadow filling the pit, dust hanging in the light.
Textures of splintered timber, mud, rusted tube, wet concrete, standing
water far below. Atmosphere of danger that is indistinguishable from
routine. No readable text, no logos, no watermarks, no visible face,
photorealistic, cinematic film still, high detail.
```

## Смысловая метафора

Главный тезис статьи в первом абзаце: опасные условия не выглядят
опасными, иначе они не дожили бы до подписания. Кадр показывает не
формулировки, а настил, где несколько досок ничем не отличаются от
остальных и при этом не лежат ни на чём.

---

## Запасная концепция

Если основной кадр выйдет плоским — генератор часто рисует мостик сверху,
и подставы под настилом не видно, а без неё смысла нет.

**Название концепции:** Строп, у которого пряди перерезаны внутри оплётки

```
Wide cinematic film still at dusk on a construction site, camera close on
a crane hook at head height. A thick steel lifting sling loops through the
hook, its outer sleeve clean, taut and reassuring along its whole visible
length; at one point the sleeve has split open and inside the wire strands
are frayed, rust-eaten and half parted, bright broken ends catching amber
light. Above and behind, a heavy palletised load hangs on that sling,
dark against the sky. A lone rigger in a hard hat stands directly beneath,
seen from behind in silhouette, one arm raised to steady the load, looking
up, not at the split. Tower cranes and unfinished concrete floors recede
into volumetric haze under a burning amber sky. Hard backlight through the
rigging, deep blue-grey shadows on the underside of the load, dust
suspended in the beams. Textures of oiled steel wire, rust, worn canvas,
concrete dust, grime. Atmosphere of a failure already present and not yet
noticed. No readable text, no logos, no watermarks, no visible face,
photorealistic, cinematic film still, high detail.
```

Тот же механизм — разрушение спрятано под ровной поверхностью, — но
объект ближе и читается быстрее в ленте. Брать, если первый вариант не
покажет пустоту под досками.

---

## После генерации

Файл кладётся в `assets/` под именем
`krasnye-flagi-dogovora-subpodryada.png` — ссылки на него уже стоят.
Проверить: букв и цифр в кадре нет, лицо не видно, палитра совпадает с
соседними обложками.
