# Обложка: дополнительные работы в строительстве

Для нового разбора `articles/dopolnitelnye-raboty-v-stroitelstve.html`
(волна В-2, запрос 1 029, товар P2).

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Пристройка, которой нет в чертеже

## Готовый промт

```
Wide cinematic film still at dusk on a construction site. In the middle
distance stands a building under construction, its main volume orderly and
measured — even floors, aligned formwork, disciplined scaffolding. Growing
sideways out of its flank is an unplanned extension built of the same
concrete and block but visibly improvised: mismatched levels, props
wedged at angles, scaffolding lashed on rather than assembled, a raw
opening cut through the finished wall to join it. The addition is
substantial, larger than it first appears, and casts its own shadow across
the disciplined part. In the immediate foreground a lone worker in a hard
hat and dirty jacket stands seen from behind in silhouette, one arm raised
mid-gesture toward the extension, holding nothing. Tower cranes and
volumetric haze behind under a burning amber sky with heavy clouds. Strong
backlight from beyond the building, deep blue-grey shadows over the
improvised part, dust hanging in the beams. Textures of fresh grey
concrete, raw block, unpainted timber props, bent scaffold tube, wet mud,
torn polyethylene. Atmosphere of real volume that grew outside the plan and
now has to be explained. No readable text, no logos, no watermarks, no
visible face, photorealistic, cinematic film still, high detail.
```

## Смысловая метафора

Дополнительный объём — не мелочь на полях, а пристройка в размер задачи:
он реально построен и реально стоит денег, но растёт сбоку от согласованной
конструкции. Пока он не пристыкован документом, он держится на подпорках.

---

## Запасная концепция

Если основной кадр выйдет нечитаемым — генератор склонен превращать
пристройку в трущобу и терять связь с организованной стройкой.

**Название концепции:** Устное поручение весом в тонну

```
Wide cinematic film still at dusk on a construction site. A heavy steel
lifting hook hangs at the centre of the frame at eye level, empty and
still, its throat wide open. Suspended from it by a single frayed sling is
an enormous concrete block, far heavier than the sling can be rated for,
hanging low over the mud. The block is unmarked and unlabelled. In the
immediate foreground a lone worker in a hard hat and dirty jacket stands
beneath its shadow, seen from behind in silhouette, looking up. Tower
cranes and half-built floors recede into volumetric haze under a burning
amber sky. Strong backlight through the sling fibres, deep blue-grey
shadows under the block, dust in the beams. Textures of cold forged steel,
worn synthetic sling, coarse concrete, rust streaks, wet mud. Atmosphere of
a weight accepted on a word. No readable text, no logos, no watermarks, no
visible face, photorealistic, cinematic film still, high detail.
```

Читается как «взято на себя без крепления». Брать, если первый вариант не
сработает.

---

## Что ушло в генерацию

Промт выше писался отдельным кадром, а обложки идут серией с постоянными
образами (решение владельца 02.08.2026). Поэтому в прогон ушёл не он, а
сюжет, встроенный в серию: описание предметов копируется в промт дословно
из блока `cast`, а сюжет говорит только, что предмет делает. Файл серии —
`ai-business-os/projects/marzha_v_betone/production/covers/prompts-articles.yaml`.

**Постоянные образы в кадре:** dopnik, master.

**Надпись серии:** Объём вырос раньше, чем его описали

```
Wide cinematic film still at dusk on a construction site. In the middle distance a building under construction stands orderly and measured — even floors, aligned formwork, disciplined scaffolding. Growing sideways out of its flank is a substantial unplanned extension of the same concrete and block, visibly improvised: mismatched levels, timber props wedged at angles, scaffolding lashed on rather than assembled, a raw opening cut through the finished wall to join it. The addition is large enough to cast its own shadow across the disciplined part. In the immediate foreground Dopnik lies flat on a plank trestle directly beneath the extension, the finished improvised structure filling the frame above it, its hollow sleeve corner catching the low sun. Master stands beside the trestle seen from behind in silhouette, one arm raised mid-gesture toward the extension, holding nothing. Tower cranes and volumetric haze behind under a burning amber sky. Strong backlight from beyond the building, deep blue-grey shadows over the improvised part, dust in the beams. Textures of fresh grey concrete, raw block, unpainted timber props, bent scaffold tube, wet mud, scratched dusty plastic. Atmosphere of real volume that grew outside the plan.
```

Прогон 11.08.2026, `google/gemini-3.1-flash-image`, пресет 1K — 1376×768.
Промт выше по документу оставлен как запасной: он самостоятелен и не
опирается на серию.

---

## После генерации

Файл кладётся в `assets/` под именем
`dopolnitelnye-raboty-v-stroitelstve.jpg` — ссылка на него стоит в статье.
Проверить: букв и цифр в кадре нет, лицо не видно, палитра совпадает с
соседними обложками, пристройка читается как незапланированный объём, а не
как ветхое строение.
