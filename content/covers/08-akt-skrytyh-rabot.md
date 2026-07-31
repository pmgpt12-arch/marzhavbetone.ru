# Обложка: акт скрытых работ

Заменяет `assets/akt-skrytyh-rabot-obrazec.png` — текстовую карточку из
`build_cover.py`. Используется в статье на сайте и в списке разборов:
меняется один файл — меняется везде.

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

То, что закрыл бетон

## Готовый промт

```
Wide cinematic film still at dusk on a construction site. In the immediate
foreground, a dense grid of steel reinforcement bars rises out of a
formwork pit, wet and rust-flecked, catching low amber rim light along
every rod. Behind it, a concrete pump hose is already discharging: a thick
grey flow pours down over the far end of the same grid and swallows it,
the bars vanishing under the mass mid-frame so that the left half of the
image is exposed structure and the right half is blank poured surface. A
lone worker in a hard hat and dirty jacket stands at the edge of the pit,
seen from behind in silhouette, one arm half-raised, too late to stop the
pour. Tower cranes and unfinished concrete floors recede into volumetric
haze under a burning amber sky with heavy clouds. Strong backlight from
behind the pour, deep blue-grey shadows in the foreground, dust and
moisture suspended in the beams. Textures of wet raw concrete, rusted
ribbed steel, splintered plywood formwork, mud, standing water.
Atmosphere of a last irreversible moment, of evidence disappearing while
someone watches. No readable text, no logos, no watermarks, no visible
face, photorealistic, cinematic film still, high detail.
```

## Смысловая метафора

Скрытые работы можно проверить ровно один раз — в короткий промежуток
между окончанием работы и её закрытием. Кадр показывает не документ, а сам
момент, после которого объём остаётся только на бумаге: половина сцены ещё
доказуема, половина уже нет.

---

## Запасная концепция

Если основной кадр выйдет слишком технологичным — генератор любит
превращать заливку в аккуратный производственный репортаж, и тревога
пропадает.

**Название концепции:** Стена, которую придётся вскрывать

```
Wide cinematic film still at dusk inside a half-built concrete structure.
A finished monolithic wall fills the centre of the frame, smooth and
featureless, with a single rough breach hacked through it at chest height;
inside the breach, exposed reinforcement and broken aggregate glow in
narrow amber light from a work lamp on the floor. Sledgehammer and dust
sheet lie abandoned in the foreground. A lone worker in a hard hat, seen
from behind in silhouette, leans in toward the opening with a torch. Deep
blue-grey shadows across the untouched wall, volumetric haze, burning
amber light source inside the breach only. Textures of raw concrete,
rusted steel, concrete dust, torn polyethylene. Atmosphere of destroying
finished work to prove something that should have been recorded earlier.
No readable text, no logos, no watermarks, no visible face, photorealistic,
cinematic film still, high detail.
```

Читается как «доказывать придётся ломая»: ближе к последствиям, дальше от
момента выбора. Брать, если первый вариант не сработает.

---

## После генерации

Файл кладётся в `assets/` под именем `akt-skrytyh-rabot-obrazec.png` —
ссылки на него уже стоят. Проверить: букв в кадре нет, лицо не видно,
палитра совпадает с соседними обложками.
