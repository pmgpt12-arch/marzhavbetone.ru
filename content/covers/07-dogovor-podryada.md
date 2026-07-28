# Обложка: комплект «Договор субподряда»

Страница `products/p7-dogovor-podryada.html` пока берёт обложку статьи
«Всё включено в цену» — она про опасное условие договора, поэтому не
выглядит чужой. Но у комплекта должен быть свой кадр: обложка статьи уже
работает в другом месте, и в выдаче они начнут конкурировать.

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Подпись, после которой торг закончен

## Готовый промт

```
Wide cinematic film still at dusk. In the immediate foreground, an
oversized industrial steel bear trap lies open on a rough concrete slab,
its jaws rusted and wet, a single sheet of paper resting on the pressure
plate. A worker's gloved hand reaches toward the paper from the right
edge of the frame, holding a pen. Behind the trap the site opens up:
tower cranes, half-built concrete floors and stacked rebar receding into
heavy volumetric haze under a burning amber sky. Strong backlight from
behind the cranes throws the trap into deep blue-grey shadow while its
teeth catch warm rim light. Textures of rusted steel, raw concrete, wet
mud, worn leather glove and thin paper. Atmosphere of a decision about to
be made that cannot be taken back. No readable text, no logos, no
watermarks, no visible face, photorealistic, cinematic film still, high
detail.
```

## Смысловая метафора

Условия договора обсуждаются один раз — до подписи. После неё остаётся
доказывать, а не договариваться. Кадр — момент, когда рука уже тянется к
бумаге, а механизм вокруг неё уже взведён.

---

## После генерации

Файл кладётся в `assets/` под именем `dogovor-subpodryada.png`, после чего
в `products/p7-dogovor-podryada.html` заменяются три ссылки:
`og:image`, `image` в разметке Product и `src` в блоке `product-hero`.
