import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def update_existing_manifests():
    print("\n[UPDATE] Existing manifests")
    
    # 01-zakrytie-rabot
    with open(os.path.join(BASE_DIR, "01-zakrytie-rabot", "MANIFEST.md"), "w", encoding="utf-8") as f:
        f.write("""# КС подписаны — денег нет

Версия: 23.07.2026

## Описание
Полный комплект для защиты подрядчика при задержке оплаты по подписанным формам КС-2 / КС-3. Включает шаблоны претензий, исковых заявлений, алгоритмы работы с исполнительным производством.

## Состав
- `01-ks-2.docx` — Word: форма КС-2
- `02-ks-3.docx` — Word: форма КС-3
- `03-akt-vypolnennyh-rabot.docx` — Word: акт выполненных работ
- `04-akt-priemki.docx` — Word: акт приемки
- `05-peredatochnyy-akt.docx` — Word: передаточный акт
- `06-zhurnal-obemov.xlsx` — Excel: журнал объемов
- `07-reestr-zamechaniy.xlsx` — Excel: реестр замечаний
- `08-reestr-peredachi.xlsx` — Excel: реестр передачи
- `09-checklist-peredachi.pdf` — PDF: чек-лист передачи
- `10-sroki-hraneniya.pdf` — PDF: сроки хранения

## Бесплатный микропродукт
`00-free-ks-podpisany-deneg-net` — "КС подписаны, денег нет: первые 7 проверок"

## Ограничение
Материалы являются редактируемыми шаблонами и требуют адаптации под договор, проект, систему документооборота и фактические обстоятельства объекта.

## Ценовая гипотеза
14 900–19 900 ₽
""")
    print("  [Updated] 01-zakrytie-rabot/MANIFEST.md")
    
    # 02-dopraboty-bez-poter
    with open(os.path.join(BASE_DIR, "02-dopraboty-bez-poter", "MANIFEST.md"), "w", encoding="utf-8") as f:
        f.write("""# Допы не в подарок

Версия: 23.07.2026

## Описание
Полный комплект для фиксации и оплаты дополнительных объемов работ. Включает допсоглашения, калькуляторы, алгоритмы согласования с заказчиком.

## Состав
- `01-prikaz-na-dopobem.docx` — Word: приказ на допобъем
- `02-soglasovanie-obema.docx` — Word: согласование объема
- `03-uvedomlenie-o-doprabotah.docx` — Word: уведомление о допработах
- `04-akt-skrytyh-rabot.docx` — Word: акт скрытых работ
- `05-izmenenie-srokov.docx` — Word: изменение сроков
- `06-pismo-o-priostanovke.docx` — Word: письмо о приостановке
- `07-raschet-stoimosti.xlsx` — Excel: расчет стоимости
- `08-zhurnal-doprabot.xlsx` — Excel: журнал допработ
- `09-checklist-fotofiksacii.pdf` — PDF: чек-лист фотофиксации
- `10-algoritm-doprabot.pdf` — PDF: алгоритм допработ

## Бесплатный микропродукт
`00-free-dopy-ne-v-podarok` — "Допы не в подарок"

## Ограничение
Материалы являются редактируемыми шаблонами и требуют адаптации под договор, проект, систему документооборота и фактические обстоятельства объекта.

## Ценовая гипотеза
14 900–19 900 ₽
""")
    print("  [Updated] 02-dopraboty-bez-poter/MANIFEST.md")
    
    # 04-polnyy-komplekt-pto
    with open(os.path.join(BASE_DIR, "04-polnyy-komplekt-pto", "MANIFEST.md"), "w", encoding="utf-8") as f:
        f.write("""# Полный комплект: Защита маржи объекта

Версия: 23.07.2026

## Описание
Полный комплект ПТО для защиты маржи строительного объекта. Включает все базовые пакеты (закрытие работ, допработы, договор подряда) плюс дополнительные инструменты для комплексного управления документацией.

## Состав
### Базовые пакеты (01-30)
- `01-30-bazovye-pakety/01-zakrytie-rabot/` — пакет "КС подписаны — денег нет"
- `01-30-bazovye-pakety/02-dopraboty-bez-poter/` — пакет "Допы не в подарок"
- `01-30-bazovye-pakety/03-dogovor-podryada/` — пакет "Договор подряда"

### Дополнительные файлы (31-40)
- `31-pyat-aktov-skrytyh-rabot.docx` — Word: 5 актов скрытых работ
- `32-shablon-ispolnitelnoy-shemy.docx` — Word: шаблон исполнительной схемы
- `33-akt-peredachi-komplekta-pto.docx` — Word: акт передачи комплекта ПТО
- `34-sluzhebnaya-zapiska.docx` — Word: служебная записка
- `35-obshiy-zhurnal-rabot.xlsx` — Excel: общий журнал работ
- `36-vhodnoy-kontrol.xlsx` — Excel: входной контроль
- `37-reestr-pasportov.xlsx` — Excel: реестр паспортов
- `38-reestr-id.xlsx` — Excel: реестр ИД
- `39-algoritm-zamechaniy.pdf` — PDF: алгоритм замечаний
- `40-ezhemesyachnaya-proverka.pdf` — PDF: ежемесячная проверка

## Бесплатные микропродукты
- `00-free-ks-podpisany-deneg-net`
- `00-free-dopy-ne-v-podarok`
- `00-free-ks-bez-vozvrata`

## Ограничение
Материалы являются редактируемыми шаблонами и требуют адаптации под договор, проект, систему документооборота и фактические обстоятельства объекта.

## Ценовая гипотеза
49 900–69 900 ₽
""")
    print("  [Updated] 04-polnyy-komplekt-pto/MANIFEST.md")


if __name__ == "__main__":
    update_existing_manifests()
    print("\nГОТОВО: manifests updated")
