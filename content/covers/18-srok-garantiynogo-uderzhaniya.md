# Обложка: срок гарантийного удержания

Заменяет `assets/srok-garantiynogo-uderzhaniya.png` — текстовую карточку
из `build_cover.py`. Используется в статье на сайте и в списке разборов:
меняется один файл — меняется везде.

Сделано по системному промпту из `PROMPT.md`.

Имя файла отличается от короткого варианта намеренно: `check_covers.py`
ищет промпт по первым двенадцати символам имени обложки, и файл должен
содержать строку `srok-garanti`, иначе проверка сообщает «ПРОМПТА НЕТ».

---

## Название концепции

Струна, у которой дальний конец на крюке

## Готовый промт

```
Wide cinematic film still at dusk on a large construction site, camera low
over a concrete slab. In the immediate foreground a steel pin is driven
hard into the slab and a string line is made fast to it, the knot tight,
the anchor absolutely solid — this end is finished, sure, and belongs to
the man in the frame. The line runs away from the camera dead straight
across the slab, taut and glowing where amber light catches it, and
dissolves into deep fog at the middle distance. Far off inside that fog,
barely readable as a shape, its other end is not tied to anything fixed at
all: it is looped over a crane hook hanging free in the air, and the hook
is drifting slowly sideways in the wind, dragging the far end with it. A
lone subcontractor in a hard hat and dirty jacket crouches at the near
pin, seen from behind in silhouette, sighting along the line into the fog.
Tower cranes and unfinished concrete floors are only silhouettes in the
haze under a burning amber sky. Hard backlight down the length of the
line, deep blue-grey shadow across the slab, thick volumetric fog.
Textures of raw concrete, rusted pin, waxed cord, mud, standing water.
Atmosphere of a measurement that is exact from a starting point somebody
else keeps moving. No readable text, no logos, no watermarks, no visible
face, photorealistic, cinematic film still, high detail.
```

## Смысловая метафора

Статья разводит две части условия: срок выражен числом и выглядит
надёжным, но отсчитывается от события, а событие вроде ввода объекта в
эксплуатацию принадлежит третьим лицам. Кадр показывает не календарь, а
натянутую струну, у которой ближний конец забит намертво, а дальний висит
на качающемся крюке в тумане.

---

## Запасная концепция

Если основной кадр окажется слишком тонким — генератор теряет дальний
конец в тумане вместе со смыслом, и остаётся просто разметка на плите.

**Название концепции:** Ваш пролёт вымыт, остальные нет

```
Wide cinematic film still at dusk on the vast raw floor plate of an
unfinished building. In the foreground one single bay is finished:
swept clean, sealed, edges cut true, cordoned off with a taut rope on
light stands, immaculate and warm-lit — one crew's work, complete. Every
other bay around it and beyond it is still raw and abandoned mid-job:
piled rubble, spilled mortar, tangled offcuts, propped formwork, other
people's tools left where they fell, stretching away in every direction
into volumetric haze. A lone subcontractor in a hard hat and dirty jacket
stands at the rope of his own clean bay, seen from behind in silhouette,
hands at his sides, done and unable to leave. Far away across the mess a
lit exit opening burns warm amber. Strong backlight from that opening,
deep blue-grey shadows across the debris field, dust hanging in the air.
Textures of swept sealed concrete, broken aggregate, dried mortar, rusted
mesh, torn polyethylene. Atmosphere of being finished and still held by
work that is not yours. No readable text, no logos, no watermarks, no
visible face, photorealistic, cinematic film still, high detail.
```

Это ловушка из таблицы событий: «устранение всех замечаний по объекту» —
слова «всех» и «по объекту» ставят возврат ваших денег в зависимость от
чужих недоделок. Брать, если первый вариант не соберётся композиционно.

---

## После генерации

Файл кладётся в `assets/` под именем `srok-garantiynogo-uderzhaniya.png` —
ссылки на него уже стоят. Проверить: букв и цифр в кадре нет, лицо не
видно, палитра совпадает с соседними обложками.
