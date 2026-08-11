# Обложка: заказчик не оплачивает выполненные работы

Для нового разбора `articles/zakazchik-ne-oplachivaet-vypolnennye-raboty.html`
(волна В-2, запрос 837, товар T1).

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Мост, достроенный до половины оплаты

## Готовый промт

```
Wide cinematic film still at dusk on a construction site. In the middle
distance a completed concrete structure stands finished and lit — formwork
stripped, edges clean, every floor closed. Running toward the viewer from
its base is a heavy suspended walkway of steel and concrete that simply
stops in mid-air a third of the way across, its severed end showing bright
torn reinforcement bars against the dark, with nothing beneath but haze.
On the near side of the gap, in the immediate foreground, a lone worker in
a hard hat and dirty jacket stands at the broken edge seen from behind in
silhouette, one hand resting on a cold steel handrail that ends with the
deck. Tower cranes idle behind, half-built floors receding into volumetric
haze under a burning amber sky with heavy clouds. Strong backlight from
behind the finished structure, deep blue-grey shadows across the foreground
deck, dust hanging in the beams. Textures of cured concrete, cut rebar
ends, cold galvanised steel, wet mud, worn safety tape. Atmosphere of work
that arrived at the far side while payment stopped short. No readable text,
no logos, no watermarks, no visible face, photorealistic, cinematic film
still, high detail.
```

## Смысловая метафора

Объект достроен, а путь к деньгам обрывается на треть пути — обрыв не в
работе, а в расчёте. Человек стоит на своей стороне разрыва: он всё
сделал, и именно поэтому дальше идти некуда без документа.

---

## Запасная концепция

Если основной кадр уйдёт в фантастику — генератор любит превращать
оборванную эстакаду в руину после катастрофы, и читается это как авария, а
не как неоплата.

**Название концепции:** Ключи переданы, касса заперта

```
Wide cinematic film still at dusk on a construction site. A heavy steel
site cabin door fills the middle of the frame, shut and secured with a
thick new padlock, its shackle catching the last light. Hanging on a nail
beside the door, in the immediate foreground and sharply lit, is a single
worn ring of keys with a concrete-dusted tag — handed over, no longer
needed. A lone worker in a hard hat and dirty jacket stands before the
locked door seen from behind in silhouette, arms at his sides. Behind the
cabin the finished structure rises complete, tower cranes idle, volumetric
haze under a burning amber sky. Strong backlight over the roofline, deep
blue-grey shadows on the door face, dust in the beams. Textures of
scratched steel sheet, cold hardened padlock, dusty brass keys, wet mud,
peeling paint. Atmosphere of a job delivered into a door that closed
afterwards. No readable text, no logos, no watermarks, no visible face,
photorealistic, cinematic film still, high detail.
```

Читается как «результат отдан, доступ к расчёту закрыт». Брать, если
первый вариант не сработает.

---

## Что ушло в генерацию

Промт выше писался отдельным кадром, а обложки идут серией с постоянными
образами (решение владельца 02.08.2026). Поэтому в прогон ушёл не он, а
сюжет, встроенный в серию: описание предметов копируется в промт дословно
из блока `cast`, а сюжет говорит только, что предмет делает. Файл серии —
`ai-business-os/projects/marzha_v_betone/production/covers/prompts-articles.yaml`.

**Постоянные образы в кадре:** kaeski, master, genpodryad.

**Надпись серии:** Подписано обеими сторонами, оплачено ни одной

```
Wide cinematic film still at dusk on a construction site. A heavy site-office table of scratched steel stands close to camera, its top wet from rain and mirroring the low sun. Kaeski lies flat at the centre of the table, both sheets squared up and fully signed, held down against the draught by a clean glass paperweight — the work is closed and nobody disputes it. Across the table, an empty folding chair faces the documents with a payment terminal lying face down beside it, its cable unplugged and coiled. Genpodryad reaches the frame only as a clean cuff and a hand resting on the far edge of the table, already withdrawing out of shot. Master stands on the near side seen from behind in silhouette, both hands flat on the steel beside the acts, waiting. Behind them the finished structure rises complete, tower cranes idle, volumetric haze under a burning amber sky. Strong backlight over the roofline, deep blue-grey shadows across the wet table, dust hanging in the beams. Textures of wet scuffed steel, damp paper, rust at the table welds, mud on boots, cold coiled cable. Atmosphere of a settled account that has stopped moving.
```

Прогон 11.08.2026, `google/gemini-3.1-flash-image`, пресет 1K — 1376×768.
Промт выше по документу оставлен как запасной: он самостоятелен и не
опирается на серию.

---

## После генерации

Файл кладётся в `assets/` под именем
`zakazchik-ne-oplachivaet-vypolnennye-raboty.jpg` — ссылка на него стоит в
статье. Проверить: букв и цифр в кадре нет, лицо не видно, палитра
совпадает с соседними обложками, обрыв читается как незавершённость
расчёта, а не как разрушение.
