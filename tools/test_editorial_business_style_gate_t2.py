"""Regression: Excel disclaimer heading must block nomination; legal negations stay valid."""
import unittest
from io import BytesIO
from zipfile import ZipFile
from editorial_business_style_gate import check

class T2EditorialRegression(unittest.TestCase):
    def test_owner_rejected_r2_language(self):
        for text in ('запуск оплаты','Быстрый запуск за 60 минут',
                     'назовите её по объекту и договору','Длина ямы',
                     'Что этот лист не решает','Что эти суммы не означают',
                     'Число в этот файл намеренно не записано',
                     'Числом в файле не задан намеренно'):
            self.assertTrue(check('sample.txt',text.encode()),text)

    def test_comment_text_is_checked(self):
        stream=BytesIO()
        with ZipFile(stream,'w') as z:
            z.writestr('xl/comments/comment1.xml', '<comments><comment><text><t>Ради этой колонки опись и существует</t></text></comment></comments>')
        self.assertTrue(check('book.xlsx',stream.getvalue()))

    def test_disclaimer_heading_variants(self):
        for text in ('Что эта опись не делает', 'Чего этот комплект не делает',
                     'Что данный документ не делает', 'Чего данная опись не делает'):
            with self.subTest(text=text):
                self.assertTrue(check('fragment.txt', text.encode()))

    def test_recurrence_from_batch_review(self):
        for phrase in (
            "Чего в этом файле нет намеренно",
            "Чего эта таблица не считает",
            "Почему файл открывается и в LibreOffice",
            "Значений здесь нет намеренно",
            "будет считаться согласованной в соответствии с п. [номер] Договора",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(check("fragment.txt",phrase.encode()),phrase)

    def test_explanatory_workbook_headings(self):
        for phrase in ("Что этот файл делает", "Чего он не делает"):
            self.assertTrue(check("fragment.txt", phrase.encode()), phrase)

    def test_hidden_self_justification_variants(self):
        for fragment in ("Что это не заменяет", "Важно: шаблон не заменяет анализ договора",
                         "Не является гарантией оплаты", "Не вычитан юристом"):
            with self.subTest(fragment=fragment):
                self.assertTrue(check("fragment.txt", fragment.encode()))

    def test_preserve_legally_meaningful_negations(self):
        for text in ('Настоящий акт не является признанием требований.',
                     'Подпись подтверждает получение документации.',
                     'Оплата не подтверждена. Обязанность не переходит.'):
            with self.subTest(text=text):
                self.assertEqual([], check('fragment.txt', text.encode()))

if __name__=='__main__': unittest.main()
