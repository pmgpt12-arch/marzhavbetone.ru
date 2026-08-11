# Обложка: какие работы относятся к скрытым

Для нового разбора `articles/akty-skrytyh-rabot-kakie.html`
(волна В-3, кластер «акт скрытых работ», товар P4).

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Скрытым делает не название, а то, что сверху

## Смысловая метафора

Список «какие работы скрытые» читатель ищет как перечень названий, а
скрытой работу делает не название, а следующая операция: то, что ляжет
сверху и закроет её от глаза. Поэтому в кадре не список, а последний час
арматурного основания под уже подведённым бетоноводом — граница между «ещё
видно» и «уже нет».

## Что ушло в генерацию

Обложки идут серией с постоянными образами (решение владельца 02.08.2026):
описание предмета копируется в промт дословно, а сюжет говорит только, что
предмет делает. Файл серии —
`ai-business-os/projects/marzha_v_betone/production/covers/prompts-articles.yaml`.

**Постоянных образов в кадре нет, и это сделано намеренно.** Ссылка на
`cast` здесь снята. `tools/generate_covers.py` собирает промт строками вида
`- {name}: {appearance}`, то есть латинское имя образа уходит в промт
текстом — и модель дважды написала `Akt skrytyh` читаемой латиницей прямо
на бумаге, против правила серии «ни букв, ни цифр». Описание предмета в
этом сюжете вставлено в промт дословно, но без имени, и к нему добавлено
прямое требование пустого листа. Третий прогон вышел чистым.

Это не про один кадр: любой сюжет, где предмет `cast` — бумага, наследует
ту же поломку. Правку самого `generate_covers.py` не делаю — она меняет
поведение общего инструмента для всех проектов и идёт предложением по
Р-047.

**Надпись серии:** Скрытым делает не название, а то, что сверху

```
Wide cinematic film still at dusk on a construction site. The frame is taken low and close over a freshly tied reinforcement mat spanning the whole foreground — bar crossings, tie wire, plastic spacers, mud between the bars — a surface that will be gone within the hour. A concrete pump boom hangs above it, chute already swung into position and dripping, poised to bury everything below. Lying on the mat at the near edge is the following object, and it is completely blank: A single grey-white sheet speckled with dried cement splash, held on a clipboard of scuffed dark hardboard with a bent steel clip. Three signature lines at the bottom edge: two carry ink, the third is empty except for a dry scratch where a pen was pressed and did not take. The sheet carries no printing, no ruling, no handwriting, no stamp and no signature — not a single character of any alphabet appears anywhere in the image. A lone worker in a hard hat and dirty work jacket crouches at the far edge of the mat, seen from behind in silhouette, one gloved hand flat on the bars, looking along them rather than up at the boom. Tower cranes and half-built floors recede into volumetric haze under a burning amber sky. Strong backlight along the bar tops, deep blue-grey shadows between them, dust and drifting cement haze in the beams. Textures of ribbed rust, tie wire, plastic spacers, wet mud, dry blank paper. Atmosphere of the last minute in which something can still be recorded.
```

Прогон 11.08.2026, `google/gemini-3.1-flash-image`, пресет 1K — 1376×768,
$0,0675 за принятый кадр. Считая две забракованные попытки, сюжет стоил
$0,20.

## Что в принятом кадре осталось от брака

На листе остались три штриха на месте подписей — нечитаемые росчерки без
единой буквы. Запрет серии сформулирован про читаемый текст, цифры и
латиницу, и по нему кадр проходит; требование «лист полностью пустой» стояло
в промте против латиницы, а не само по себе. Четвёртый прогон не запускал:
он стоит ещё $0,067 и возвращает риск, ради которого промт и переписан.

---

## После генерации

Файл лежит в `assets/akty-skrytyh-rabot-kakie.jpg` — ссылка на него стоит в
статье. Проверено на принятом кадре: читаемых букв и цифр нет, лицо не
видно, палитра совпадает с соседними обложками кластера, бетоновод читается
как то, что закроет арматуру, а не как случайная техника в кадре.
