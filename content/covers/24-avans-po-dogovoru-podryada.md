# Обложка: аванс по договору подряда

Для `articles/avans-po-dogovoru-podryada.html` — «Аванс по договору
подряда: почему работа начинается на ваши деньги».

Обложка у страницы уже стоит: `assets/avans-po-dogovoru-podryada.jpg`,
1376×768, пустая площадка на рассвете — техника заведена, материала нет.
Промпта к ней в репозитории не было, и переделать её, не придумывая
концепцию заново, было нечем. Этот файл закрывает пробел и одновременно
берёт узел точнее — почему, сказано в разделе «Чем отличается от
действующей».

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Линия подачи бетона, собранная и пустая

## Готовый промт

```
Wide cinematic film still at first light on a construction site, camera low
and close beside freshly built wall formwork. A heavy concrete pump line
runs from the foreground deep into the frame: steel delivery pipes and a
thick rubber hose, every clamp closed, every coupling seated and locked,
the whole line properly rigged back to a pump truck standing ready at the
far end, boom raised and in position. The hose lies slack and flat,
collapsed along its entire length, nothing moving through it, its open end
resting over the formwork where the pour should already be happening. The
formwork stands clean and dry, tie rods and rebar cage waiting, not a trace
of concrete inside it. A lone subcontractor in a hard hat and dirty jacket
stands at the near end, seen from behind in silhouette, one gloved hand
laid on the dead hose, motionless, waiting. Tower cranes and an unfinished
concrete frame recede into volumetric haze under a cold amber dawn sky.
Hard backlight running the length of the pipeline turning the steel into a
bright ribbon, deep blue-grey shadow pooling inside the empty formwork,
dust and thin ground fog suspended in the light. Textures of oiled steel,
cracked rubber, rusted clamps, raw plywood, cold rebar, wet mud. Atmosphere
of a system fully connected and delivering nothing. No readable text, no
logos, no watermarks, no visible face, photorealistic, cinematic film
still, high detail.
```

## Смысловая метафора

Главный тезис страницы — строчка «аванс предусмотрен» не двигает кассу.
Кадр показывает не отсутствие денег, а собранную линию, по которой ничего
не идёт: хомуты затянуты, насос на месте, соединение оформлено полностью,
и ровно ноль на выходе. Пока в договоре не названы срок, событие отсчёта и
порядок погашения, он описывает трубу, а не поток.

---

## Запасная концепция

Если основной кадр выйдет нечитаемым — риск в том, что генератор нарисует
рукав объёмным и напряжённым, и «пусто» пропадёт: зритель прочитает
обычную заливку. Плоский спавший рукав модель держит плохо.

**Название концепции:** Заправочный пистолет, вставленный в сухой бак

```
Wide cinematic film still at first light on a construction site, camera
close on the fuel tank of a heavy excavator, filler neck at frame centre. A
fuel nozzle is inserted into the open tank and left hanging there, its
trigger clipped down in the delivery position, the hose running back out of
frame slack and flat on the mud. Nothing is flowing: the spout is dry, and
down inside the filler the tank shows bare dark metal, empty. The excavator
sits ready for the shift, engine cowling open, bucket lowered into
untouched ground, tracks clean. A lone operator in a hard hat and dirty
jacket stands beside the machine, seen from behind in silhouette, one hand
resting on the fender, looking at the nozzle. Tower cranes and an
unfinished concrete frame recede into volumetric haze under a cold amber
dawn sky. Hard backlight raking across the machine flank turning wet steel
into a bright edge, deep blue-grey shadow under the belly of the excavator,
dust and thin ground fog hanging in the beams. Textures of oiled steel,
scratched paint, rusted filler ring, rubber hose, cold mud. Atmosphere of
readiness that cannot start. No readable text, no logos, no watermarks, no
visible face, photorealistic, cinematic film still, high detail.
```

Тот же механизм — всё подключено и подано ноль, — но объект один и
крупный, поэтому читается в ленте за долю секунды. Брать, если на первом
варианте не видно, что рукав пуст.

---

## Чем отличается от действующей

Действующая обложка говорит «материала нет» — это следствие. Оба промта
выше говорят «канал собран, поток нулевой» — это причина, и она же
единственный тезис страницы: подпись под пунктом об авансе не является
деньгами. Разница видна в кадре: там нет ничего, здесь есть всё, кроме
того, ради чего оно собрано.

Замена не обязательна. Действующая обложка держит палитру и метафору не
ломает — если менять её сейчас незачем, файл остаётся источником для
будущей перегенерации.

## После генерации

Файл кладётся в `assets/` под именем `avans-po-dogovoru-podryada.jpg` —
ссылки на него уже стоят, включая `og:image`. Размер брать 1376×768, как у
действующей: `check_covers.py` считает пропорции, и вертикальный кадр
обрежется по центру в превью ссылки.

Проверить в этом порядке: букв и цифр в кадре нет, лицо не видно, палитра
совпадает с соседними обложками.
