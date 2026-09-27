#!/usr/bin/env python3
"""Эталонный расчёт процентов по ст. 395 ГК РФ для книги S1.

Книга `14-raschet-procentov-395.xlsx` считает формулами; этот модуль
считает то же самое независимо, по дням, и служит эталоном в проверках:
книга, пересчитанная LibreOffice, обязана дать ту же сумму.

Правила, общие для книги и эталона (LEGAL_REVIEW_REQUIRED — см. отчёт):
- ставка вводится в процентах годовых и делится на 100 ровно один раз;
- число дней в году — фактическое для года каждого дня (365 или 366);
- оплата, поступившая в день D, уменьшает долг со дня D+1: день оплаты
  остаётся днём просрочки на прежнюю сумму;
- оплата гасит основной долг (проценты по ст. 395 не начисляются на
  проценты и в расчёте основного долга не участвуют);
- дни исключаемых периодов (например, мораторий) не начисляются;
- период — непрерывный отрезок дней с одинаковыми долгом, ставкой, числом
  дней в году и признаком исключения; проценты за период округляются до
  копейки, итог — сумма округлённых периодов.

Модуль без внешних зависимостей.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


@dataclass
class Period:
    start: date
    end: date
    debt: Decimal
    rate: Decimal
    year_days: int
    excluded: bool

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def interest(self) -> Decimal:
        if self.excluded:
            return Decimal("0.00")
        raw = self.debt * self.rate / Decimal(100) * self.days / self.year_days
        return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def year_days(d: date) -> int:
    return 366 if (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)) else 365


def calculate(principal, start: date, end: date,
              rates: list[tuple[date, float]],
              payments: list[tuple[date, float]] = (),
              excluded: list[tuple[date, date]] = ()) -> tuple[Decimal, list[Period]]:
    principal = Decimal(str(principal))
    rates = sorted((d, Decimal(str(r))) for d, r in rates)
    if not rates or rates[0][0] > start:
        raise ValueError("нет ставки на дату начала просрочки")
    pays = [(d, Decimal(str(a))) for d, a in payments]
    for d, a in pays:
        if d < start or d > end or a <= 0:
            raise ValueError(f"оплата {d} {a} вне периода расчёта или неположительна")
    periods: list[Period] = []
    day = start
    while day <= end:
        debt = principal - sum((a for d, a in pays if d < day), Decimal(0))
        if debt < 0:
            raise ValueError("оплаты превышают сумму долга")
        rate = [r for d, r in rates if d <= day][-1]
        ex = any(a <= day <= b for a, b in excluded)
        key = (debt, rate, year_days(day), ex)
        if periods and (periods[-1].debt, periods[-1].rate,
                        periods[-1].year_days, periods[-1].excluded) == key \
                and periods[-1].end + timedelta(days=1) == day:
            periods[-1].end = day
        else:
            periods.append(Period(day, day, debt, rate, year_days(day), ex))
        day += timedelta(days=1)
    total = sum((p.interest for p in periods), Decimal("0.00"))
    return total, periods


if __name__ == "__main__":
    total, periods = calculate(
        1_000_000, date(2025, 1, 10), date(2025, 3, 31),
        rates=[(date(2024, 10, 28), 21)],
        payments=[(date(2025, 2, 14), 300_000)])
    for p in periods:
        print(p.start, p.end, p.days, p.debt, p.rate, p.year_days, p.interest)
    print("итого", total)
