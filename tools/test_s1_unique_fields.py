from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent / "candidates" / "s1-oplata-za-raboty"
def text(name):
    with zipfile.ZipFile(ROOT / name) as z:
        return z.read("word/document.xml").decode()

def test_notification_distinguishes_payment_deadline_and_registry_date():
    value = text("06-uvedomlenie-o-prosrochke.docx")
    assert "{{ДАТА}}" not in value
    assert value.count("{{ДАТА_ОПЛАТЫ_ПО_ТРЕБОВАНИЮ}}") == 1
    assert value.count("{{ДАТА_РЕЕСТРА_ВЗАИМОРАСЧЁТОВ}}") == 1
    filled = value.replace("{{ДАТА_ОПЛАТЫ_ПО_ТРЕБОВАНИЮ}}", "20.10.2026").replace("{{ДАТА_РЕЕСТРА_ВЗАИМОРАСЧЁТОВ}}", "05.10.2026")
    assert "в срок до 20.10.2026" in filled
    assert "реестр взаиморасчётов на 05.10.2026" in filled

def test_claim_distinguishes_parties_and_dates_for_replace_all():
    value = text("10-obrashchenie-v-sud.docx")
    for ambiguous in ["ИНН", "ОГРН", "АДРЕС", "ДАТА"]:
        assert "{{" + ambiguous + "}}" not in value
    mapping = {"ИНН_ИСТЦА": "5003123456", "ИНН_ОТВЕТЧИКА": "7701234567", "ОГРН_ИСТЦА": "1111111111111", "ОГРН_ОТВЕТЧИКА": "2222222222222", "АДРЕС_ИСТЦА": "Адрес истца", "АДРЕС_ОТВЕТЧИКА": "Адрес ответчика", "ДАТА_ПРЕТЕНЗИИ": "01.09.2026", "ДАТА_ПОДПИСАНИЯ_ИСКА": "05.10.2026"}
    for name, replacement in mapping.items():
        assert value.count("{{" + name + "}}") == 1
        value = value.replace("{{" + name + "}}", replacement)
    assert "ИНН 5003123456, ОГРН 1111111111111, адрес: Адрес истца" in value
    assert "ИНН 7701234567, ОГРН 2222222222222, адрес (по ЕГРЮЛ): Адрес ответчика" in value
    assert "от 01.09.2026 направлена" in value
    assert "05.10.2026" in value
