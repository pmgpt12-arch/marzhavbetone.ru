"""Regression: Excel disclaimer heading must block nomination; legal negations stay valid."""
import unittest
from editorial_business_style_gate import check

class T2EditorialRegression(unittest.TestCase):
    def test_disclaimer_heading_variants(self):
        for text in ('Что эта опись не делает', 'Чего этот комплект не делает',
                     'Что данный документ не делает', 'Чего данная опись не делает'):
            with self.subTest(text=text):
                self.assertTrue(check('fragment.txt', text.encode()))

    def test_preserve_legally_meaningful_negations(self):
        for text in ('Настоящий акт не является признанием требований.',
                     'Подпись подтверждает получение документации.',
                     'Оплата не подтверждена. Обязанность не переходит.'):
            with self.subTest(text=text):
                self.assertEqual([], check('fragment.txt', text.encode()))

if __name__=='__main__': unittest.main()
