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
  копейки, итог — сумма округлённых периодов;
- несколько актов с разными датами начала просрочки считаются по отдельности
  (`calculate_acts`): у каждого акта свои периоды и своё округление, итог —
  точная сумма итогов по актам до копейки. Объединять акты в один долг
  нельзя: ни с одной датой (занижает или завышает проценты), ни по дням
  с округлением общих периодов (`calculate_combined`) — это расходится с
  суммой по актам на копейки и служит в проверках только контрастом.

Модуль без внешних зависимостей.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class Act:
    """Одна часть долга со своей датой начала просрочки.

    `debt` — основной долг на первый день просрочки (`start`), то есть уже за
    вычетом всего, что было оплачено и зачтено до этой даты. `payments` —
    только оплаты, отнесённые к этому акту и поступившие не раньше `start`.
    """
    id: str
    debt: Decimal | int | float | str
    start: date
    payments: list[tuple[date, float]] = field(default_factory=list)


@dataclass
class ActResult:
    act: Act
    total: Decimal
    periods: list[Period]

    @property
    def debt_at_end(self) -> Decimal:
        return Decimal(str(self.act.debt)) - sum(
            (Decimal(str(a)) for _, a in self.act.payments), Decimal(0))


def _check_acts(acts: list[Act]) -> None:
    if not acts:
        raise ValueError("нужен хотя бы один акт с суммой долга и датой начала просрочки")
    ids = [a.id for a in acts]
    if len(ids) != len(set(ids)):
        raise ValueError("идентификатор акта повторяется: оплату нельзя отнести однозначно")


def calculate_acts(acts: list[Act], end: date,
                   rates: list[tuple[date, float]],
                   excluded: list[tuple[date, date]] = ()) -> tuple[Decimal, list[ActResult]]:
    """Проценты по нескольким актам с разными датами начала просрочки.

    Каждый акт считается своим `calculate` (свои периоды, своё округление),
    итог — сумма итогов по актам. Общий долг не собирается нигде.
    """
    _check_acts(acts)
    out: list[ActResult] = []
    for a in acts:
        total, periods = calculate(a.debt, a.start, end, rates, a.payments, excluded)
        out.append(ActResult(a, total, periods))
    return sum((r.total for r in out), Decimal("0.00")), out


def calculate_combined(acts: list[Act], end: date,
                       rates: list[tuple[date, float]],
                       excluded: list[tuple[date, date]] = ()) -> tuple[Decimal, list[Period]]:
    """НЕ для итога. Долг дня — сумма наступивших актов, округление по периодам
    общего долга. Нужна проверкам как контраст: результат может отличаться от
    суммы по актам на копейки."""
    _check_acts(acts)
    rates = sorted((d, Decimal(str(r))) for d, r in rates)
    periods: list[Period] = []
    day = min(a.start for a in acts)
    while day <= end:
        debt = sum((Decimal(str(a.debt)) - sum((Decimal(str(s)) for d, s in a.payments if d < day), Decimal(0))
                    for a in acts if a.start <= day), Decimal(0))
        rate = [r for d, r in rates if d <= day][-1]
        ex = any(x <= day <= y for x, y in excluded)
        key = (debt, rate, year_days(day), ex)
        if periods and (periods[-1].debt, periods[-1].rate, periods[-1].year_days, periods[-1].excluded) == key:
            periods[-1].end = day
        else:
            periods.append(Period(day, day, debt, rate, year_days(day), ex))
        day += timedelta(days=1)
    return sum((p.interest for p in periods), Decimal("0.00")), periods


if __name__ == "__main__":
    total, acts = calculate_acts(
        [Act("КС-2 № 1", 700_000, date(2026, 7, 31), [(date(2026, 8, 20), 200_000)]),
         Act("КС-2 № 2", 300_000, date(2026, 8, 11))],
        end=date(2026, 9, 27), rates=[(date(2026, 1, 1), 20)])
    for r in acts:
        print(r.act.id, r.total, "долг на конец", r.debt_at_end)
        for p in r.periods:
            print("   ", p.start, p.end, p.days, p.debt, p.rate, p.year_days, p.interest)
    print("итого", total)
