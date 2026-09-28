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
- несколько актов с разными датами начала просрочки (`calculate_acts`): долг
  дня — сумма остатков всех актов, первый день просрочки которых уже наступил;
  оплата уменьшает долг своего акта со следующего дня. Акт входит в долг со
  своей даты, поэтому его начало тоже открывает новый период. Объединять акты
  в один долг с одной датой нельзя: это занижает или завышает проценты.
  Проценты по каждому акту (`ActResult.total`) — справочная разбивка без
  округления по периодам; сумма к взысканию — округлённые периоды общего долга.

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


def _day_weight(day: date, rates, excluded) -> Decimal:
    if any(a <= day <= b for a, b in excluded):
        return Decimal(0)
    rate = [r for d, r in rates if d <= day][-1]
    return rate / Decimal(100) / year_days(day)


def calculate_acts(acts: list[Act], end: date,
                   rates: list[tuple[date, float]],
                   excluded: list[tuple[date, date]] = ()) -> tuple[Decimal, list[Period], list[ActResult]]:
    """Проценты по нескольким актам с разными датами начала просрочки.

    Одна строка на календарный день: долг дня — сумма остатков актов, по
    которым просрочка уже началась. Возвращает итог (сумма округлённых
    периодов общего долга), периоды и справочную разбивку по актам.
    """
    if not acts:
        raise ValueError("нужен хотя бы один акт с суммой долга и датой начала просрочки")
    ids = [a.id for a in acts]
    if len(ids) != len(set(ids)):
        raise ValueError("идентификатор акта повторяется: оплату нельзя отнести однозначно")
    rates = sorted((d, Decimal(str(r))) for d, r in rates)
    first = min(a.start for a in acts)
    if not rates or rates[0][0] > first:
        raise ValueError("нет ставки на дату начала просрочки")
    for a in acts:
        if a.start > end:
            raise ValueError(f"акт {a.id}: первый день просрочки позже последнего дня расчёта")
        for d, s in a.payments:
            if d < a.start or d > end or Decimal(str(s)) <= 0:
                raise ValueError(f"акт {a.id}: оплата {d} {s} вне периода расчёта или неположительна")
        if sum((Decimal(str(s)) for _, s in a.payments), Decimal(0)) > Decimal(str(a.debt)):
            raise ValueError(f"акт {a.id}: оплаты превышают сумму долга")

    def act_debt(a: Act, day: date) -> Decimal:
        if day < a.start:
            return Decimal(0)
        return Decimal(str(a.debt)) - sum((Decimal(str(s)) for d, s in a.payments if d < day), Decimal(0))

    periods: list[Period] = []
    per_act = {a.id: Decimal(0) for a in acts}
    day = first
    while day <= end:
        w = _day_weight(day, rates, excluded)
        debt = Decimal(0)
        for a in acts:
            ad = act_debt(a, day)
            per_act[a.id] += ad * w
            debt += ad
        rate = [r for d, r in rates if d <= day][-1]
        ex = any(a <= day <= b for a, b in excluded)
        key = (debt, rate, year_days(day), ex)
        if periods and (periods[-1].debt, periods[-1].rate,
                        periods[-1].year_days, periods[-1].excluded) == key:
            periods[-1].end = day
        else:
            periods.append(Period(day, day, debt, rate, year_days(day), ex))
        day += timedelta(days=1)
    total = sum((p.interest for p in periods), Decimal("0.00"))
    out = [ActResult(a, per_act[a.id].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), [])
           for a in acts]
    return total, periods, out


if __name__ == "__main__":
    total, periods, acts = calculate_acts(
        [Act("КС-2 № 1", 700_000, date(2026, 7, 31), [(date(2026, 8, 20), 200_000)]),
         Act("КС-2 № 2", 300_000, date(2026, 8, 11))],
        end=date(2026, 9, 27), rates=[(date(2026, 1, 1), 20)])
    for r in acts:
        print(r.act.id, r.total, "долг на конец", r.debt_at_end)
    for p in periods:
        print("   ", p.start, p.end, p.days, p.debt, p.rate, p.year_days, p.interest)
    print("итого", total)
