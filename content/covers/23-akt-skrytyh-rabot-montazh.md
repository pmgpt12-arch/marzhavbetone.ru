# Обложка: акт скрытых работ на монтаж сетей

Для нового разбора `articles/akt-skrytyh-rabot-montazh.html`
(волна В-3, кластер «акт скрытых работ», товар P4).

Сделано по системному промпту из `PROMPT.md`.

---

## Название концепции

Между испытанием и штукатуркой

## Смысловая метафора

У монтажного узла два закрытия, и разбор держится на их порядке:
собственное испытание линии и отделка смежника, которая зашьёт штробу.
Кадр ставит оба в один план — манометр ещё под давлением, мешок сухой
смеси и сокол с раствором уже стоят рядом, — и мастер смотрит не на трубу,
а на раствор. Час, за который узел ещё можно увидеть.

## Что ушло в генерацию

Обложки идут серией с постоянными образами (решение владельца 02.08.2026):
описание предмета копируется в промт дословно из блока `cast`, а сюжет
говорит только, что предмет делает. Файл серии —
`ai-business-os/projects/marzha_v_betone/production/covers/prompts-articles.yaml`.

**Постоянные образы в кадре:** akt_skrytyh, master.

**Надпись серии:** Между испытанием и штукатуркой

```
Wide cinematic film still at dusk inside an unfinished floor of a building under construction, open to the sky along one side. A run of newly installed pipework and cable crosses the foreground wall in a cut chase — brackets set, sleeves through the wall, a pressure gauge still clamped to the line and holding. Beside it stands an opened bag of dry plaster mix and a hawk loaded with fresh mortar, waiting to close the chase. Akt skrytyh lies on a plank across two trestles directly under the run, in line with both the gauge and the mortar. Master stands at the wall seen from behind in silhouette, one hand on the pipe, head turned toward the mortar rather than the pipe. Low sun floods the open side, volumetric haze, dust suspended in the light. Strong backlight along the pipe run, deep blue-grey shadows in the chase, warm reflections on wet mortar. Textures of raw block, cut plaster edges, galvanised sleeve, brass fitting, coarse mix, dry paper. Atmosphere of a joint that has one hour left to be seen.
```

Прогон 11.08.2026, `google/gemini-3.1-flash-image`, пресет 1K — 1376×768,
$0,0684, с первой попытки.

Здесь ссылка на `cast` оставлена, и латиница на бумаге не появилась: лист
лежит мелко и в тени, а смысловой центр кадра — штроба, а не документ. Тот
же приём в соседнем сюжете (`22-akty-skrytyh-rabot-kakie.md`), где бумага
занимает передний план, дважды дал читаемую надпись. Признак риска —
крупный план бумажного предмета `cast`, а не сам `cast`.

---

## После генерации

Файл лежит в `assets/akt-skrytyh-rabot-montazh.jpg` — ссылка на него стоит
в статье. Проверено на принятом кадре: читаемых букв и цифр нет, лицо не
видно, палитра совпадает с соседними обложками кластера, манометр и раствор
читаются в одном плане.
