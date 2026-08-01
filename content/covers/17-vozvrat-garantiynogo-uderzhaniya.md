# Обложка: возврат гарантийного удержания

Заменяет `assets/vozvrat-garantiynogo-uderzhaniya.png` — текстовую
карточку из `build_cover.py`. Используется в статье на сайте и в списке
разборов: меняется один файл — меняется везде.

Сделано по системному промпту из `PROMPT.md`.

Имя файла отличается от короткого варианта намеренно: `check_covers.py`
ищет промпт по первым двенадцати символам имени обложки, и файл должен
содержать строку `vozvrat-gara`, иначе проверка сообщает «ПРОМПТА НЕТ».

---

## Название концепции

Затвор, который идёт только с храповика

## Готовый промт

```
Wide cinematic film still at dusk in a concrete drainage channel on the
edge of a construction site. A huge rusted sluice gate fills the frame,
seized shut in its guides, its whole face crusted with dried silt and
scale, plainly untouched for years. A manual ratchet lever hoist is
shackled between the gate lug and an anchor in the channel wall, its chain
bar-tight; the pawl has caught and holds every notch already won. A lone
subcontractor in a hard hat and dirty jacket hauls on the lever, seen from
behind in silhouette, whole body into it, boots braced against the
concrete. The gate has risen a finger's width and no more — and through
that gap a hard band of warm amber light and a first thin sheet of water
break out toward the camera, blindingly bright against the dark plate. The
gate itself moved for nobody until this. Tower cranes and unfinished
concrete floors recede into volumetric haze under a burning amber sky.
Deep blue-grey shadow fills the channel, dust and spray hanging in the
beam. Textures of pitted rust, dried silt, galvanised chain, wet concrete,
mud. Atmosphere of something that will not open by itself and will not
close again either. No readable text, no logos, no watermarks, no visible
face, photorealistic, cinematic film still, high detail.
```

## Смысловая метафора

Первый абзац статьи: возврат почти всегда начинается с вашего действия, а
не с их платежа — о вас не вспомнят. Кадр показывает не переписку, а
храповик: пять шагов от расчёта до претензии — это щелчки, каждый из
которых удерживает набранное и не даёт откатиться.

---

## Запасная концепция

Если основной кадр выйдет статичным — генератор часто рисует аккуратный
гидроузел без усилия, и остаётся инфраструктура вместо борьбы.

**Название концепции:** Полиспаст, привязанный к встречному грузу

```
Wide cinematic film still at dusk inside an unfinished concrete structure.
A block and tackle hangs from a steel beam in the foreground; a lone
subcontractor in a hard hat and dirty jacket hauls down on the fall line,
seen from behind in silhouette, leaning his full weight into the rope,
heels off the floor. The load he is lifting has not moved a centimetre —
because the far end of the rope, running off into the shadow at the edge
of the frame, is made fast to a second and heavier mass that nobody
mentioned, half hidden behind a stack of formwork. Rope taut in both
directions, sheaves under strain. Warm amber light rakes in from an
opening behind the load, deep blue-grey shadows swallow the hidden
counterweight, volumetric haze between them. Tower cranes and raw concrete
floors beyond. Textures of worn hemp rope, cast steel sheaves, rust, raw
concrete, dust. Atmosphere of effort quietly cancelled by something
arranged out of sight. No readable text, no logos, no watermarks, no
visible face, photorealistic, cinematic film still, high detail.
```

Это раздел «что делать, если вместо возврата пришёл зачёт»: усилие
приложено, а сумма не двинулась, потому что на другом конце повесили
встречное требование. Брать, если акцент нужен на зачёте, а не на порядке
шагов.

---

## После генерации

Файл кладётся в `assets/` под именем `vozvrat-garantiynogo-uderzhaniya.png`
— ссылки на него уже стоят. Проверить: букв и цифр в кадре нет, лицо не
видно, палитра совпадает с соседними обложками.
