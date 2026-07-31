# Обложка: строительная смета — где теряется маржа

Заменяет `assets/stroitelnaya-smeta-gde-teryaetsya-marzha.png` — текстовую
карточку из `build_cover.py`.

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Весы, у которых занижена гиря

## Готовый промт

```
Wide cinematic film still at dusk on a construction site. A massive rusted
industrial balance scale dominates the centre of the frame. Its left pan is
heaped far above the rim with real material — cement sacks, coils of rebar,
stacked timber, aggregate spilling over the edge and onto the mud. Its
right pan holds a single small counterweight, absurdly undersized, yet the
beam is locked level as though the imbalance had been agreed in advance;
the pivot is welded, not free. A lone worker in a hard hat and dirty
jacket, seen from behind in silhouette, stands at the loaded pan adding one
more sack. Tower cranes and unfinished concrete floors recede into
volumetric haze under a burning amber sky with heavy clouds. Strong
backlight behind the beam, deep blue-grey shadows in the foreground, dust
suspended in the light. Textures of pitted rust, torn paper sacks, wet mud,
raw concrete, oiled steel. Atmosphere of an exchange fixed against you
before the work began. No readable text, no logos, no watermarks, no
visible face, photorealistic, cinematic film still, high detail.
```

## Смысловая метафора

Смета — не расчёт, а граница того, что вы обязаны сделать за эти деньги.
Когда объём занижен, а обязательство остаётся полным, равновесие держится
не арифметикой, а сваренным шарниром: доложить придётся вам.

---

## Запасная концепция

Если основной кадр выйдет слишком аллегорическим — генератор любит
превращать весы в декоративный символ правосудия.

**Название концепции:** Мерная рейка, у которой стёрты деления

```
Extreme close cinematic film still at dusk. A long steel measuring staff
stands vertical in wet concrete in the foreground, filling the left third
of the frame; its lower graduations are crisp and legible as marks, but
from mid-height upward the scale is worn smooth and blank, the metal
polished bare. Behind it, deeply out of focus, a lone worker in a hard hat
seen from behind in silhouette walks away across a poured slab toward tower
cranes in volumetric haze. Burning amber backlight along the staff edge,
deep blue-grey shadow across the slab, dust in the beams. Textures of
scratched steel, wet concrete, mud, rust. Atmosphere of measurement that
stops exactly where it starts to matter. No readable text, no logos, no
watermarks, no visible face, photorealistic, cinematic film still, high
detail.
```

Читается как «мерить перестают там, где начинается ваша часть»: тоньше, но
слабее в превью. Брать, если первый вариант не сработает.

---

## После генерации

Файл кладётся в `assets/` под именем
`stroitelnaya-smeta-gde-teryaetsya-marzha.png` — ссылки на него уже стоят.
Проверить: букв в кадре нет, лицо не видно, палитра совпадает с соседними
обложками. Делений на рейке в запасном варианте быть не должно читаемыми
цифрами — модель охотно рисует числа, это нарушает правило «букв в кадре
нет».
