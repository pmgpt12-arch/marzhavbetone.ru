from pathlib import Path
from datetime import date
import copy,json
O=Path(__file__).resolve().parent;M='Реестр удержаний';T='Условия возврата'
def sn(s):return(date.fromisoformat(s)-date(1899,12,30)).days
base={M:dict(B3=sn('2026-10-23'),B9='КС-2 №1 от 15.10.2025',C9=1000000,D9=100000,E9=20000,F9=0),T:dict(B9='п. 8.1 и 8.2 договора',C9='Истечение гарантии. Акт №1 от 15.10.2025',D9=sn('2026-10-15'),E9='автоматически',G9=sn('2026-10-22'),H9='5 рабочих дней после события',I9='да',J9=sn('2026-10-20'),K9='ПП №2 от 20.10.2026',L9='Ответ и доставка по договорному каналу')}
cases=[]
def case(name,changes=None,expected=None,original=None):
 data=copy.deepcopy(base if original is None else original)
 for s,cs in(changes or{}).items():
  for c,v in cs.items():
   if v is None:data.setdefault(s,{}).pop(c,None)
   else:data.setdefault(s,{})[c]=v
 cases.append(dict(name=name,inputs=data,expected={M:expected or dict(G9=80000,H9=80000,G5=80000,H5=80000,I9='К ВОЗВРАТУ')}))
case('accepted-qa01-no-double-subtraction')
case('historical-dates-per-contract',{M:dict(B3=sn('1999-10-23')),T:dict(D9=sn('1999-10-15'),G9=sn('1999-10-22'),J9=sn('1999-10-20'))})
case('negative-excel-date',{M:dict(B3=-1)},dict(G9='ДАТА РАСЧЁТА',G5='ПРОВЕРЬТЕ РЕЕСТР'))
case('out-of-excel-date-range',{M:dict(B3=2958466)},dict(G9='ДАТА РАСЧЁТА',G5='ПРОВЕРЬТЕ РЕЕСТР'))
case('no-returns',{M:dict(E9=0),T:dict(J9=None,K9=None)},dict(G9=100000,H9=100000,E5=0,G5=100000,H5=100000))
case('fully-returned',{M:dict(E9=100000)},dict(G9=0,H9=0,G5=0,H5=0,I9='ПОГАШЕНО ПОЛНОСТЬЮ'))
case('other-confirmed-discharge',{M:dict(F9=10000),T:dict(M9=sn('2026-10-18'),K9='ПП №2; соглашение №3 от 18.10')},dict(G9=70000,H9=70000,F5=10000,G5=70000,H5=70000))
case('fully-discharged-mixed',{M:dict(F9=80000),T:dict(M9=sn('2026-10-18'),K9='ПП №2; соглашение №3 от 18.10')},dict(G9=0,H9=0,G5=0,H5=0))
case('not-yet-due',{T:dict(G9=sn('2026-10-30'))},dict(G9=80000,H9=0,G5=80000,H5=0,I9='СРОК НЕ НАСТУПИЛ'))
case('deadline-day',{T:dict(G9=sn('2026-10-23'))})
case('conditions-not-met',{T:dict(I9='нет',D9=None,G9=None)},dict(G9=80000,H9=0,G5=80000,H5=0,I9='УСЛОВИЯ НЕ ВЫПОЛНЕНЫ'))
case('conditions-unknown',{T:dict(I9=None)},dict(G9=80000,H9='ПОДТВЕРДИТЕ УСЛОВИЯ',G5=80000,H5='ПРОВЕРЬТЕ УСЛОВИЯ'))
case('conditions-disputed',{T:dict(I9='спор')},dict(G9=80000,H9='СПОРНЫЕ УСЛОВИЯ',G5=80000,H5='ПРОВЕРЬТЕ УСЛОВИЯ'))
case('first-demand-starts-period',{T:dict(E9='по требованию',F9=None,G9=None,H9='5 рабочих дней после доставки')},dict(G9=80000,H9='НАПРАВЬТЕ ТРЕБОВАНИЕ',H5='ПРОВЕРЬТЕ УСЛОВИЯ'))
case('delivered-demand-due',{T:dict(E9='по требованию',F9=sn('2026-10-15'))})
case('delivered-demand-future-due',{T:dict(E9='по требованию',F9=sn('2026-10-20'),G9=sn('2026-10-27'))},dict(G9=80000,H9=0,H5=0,I9='СРОК НЕ НАСТУПИЛ'))
case('demand-before-event-if-contract-allows',{T:dict(E9='по требованию',F9=sn('2026-10-10'))})
for name,ch,msg in [
 ('missing-event-date',dict(D9=None),'ПОДТВЕРДИТЕ СОБЫТИЕ'),
 ('event-future-but-confirmed',dict(D9=sn('2026-10-24')),'ПОДТВЕРДИТЕ СОБЫТИЕ'),
 ('text-event-date',dict(D9='не дата'),'ПОДТВЕРДИТЕ СОБЫТИЕ'),
 ('missing-deadline',dict(G9=None),'ПОДТВЕРДИТЕ СРОК'),
 ('deadline-before-event',dict(G9=sn('2026-10-14')),'ПОДТВЕРДИТЕ СРОК'),
 ('text-deadline',dict(G9='не дата'),'ПОДТВЕРДИТЕ СРОК'),
 ('missing-clause',dict(B9=None),'ОСНОВАНИЕ И СРОК'),
 ('missing-event-proof',dict(C9=None),'ОСНОВАНИЕ И СРОК'),
 ('missing-term-basis',dict(H9=None),'ОСНОВАНИЕ И СРОК'),
 ('unknown-return-mode',dict(E9='неизвестно'),'ВИД ВОЗВРАТА'),
 ('future-demand-delivery',dict(E9='по требованию',F9=sn('2026-10-24')),'ПОДТВЕРДИТЕ ДОСТАВКУ'),
 ('text-demand-delivery',dict(E9='по требованию',F9='не дата'),'ПОДТВЕРДИТЕ ДОСТАВКУ'),
 ('deadline-before-delivery',dict(E9='по требованию',F9=sn('2026-10-22'),G9=sn('2026-10-21')),'ПОДТВЕРДИТЕ СРОК')]:case(name,{T:ch},dict(G9=80000,H9=msg,H5='ПРОВЕРЬТЕ УСЛОВИЯ'))
for name,ch,msg in [
 ('negative-held',{M:dict(D9=-100000)},'ПРОВЕРЬТЕ СУММЫ'),
 ('negative-return',{M:dict(E9=-20000)},'ПРОВЕРЬТЕ СУММЫ'),
 ('negative-other-discharge',{M:dict(F9=-1)},'ПРОВЕРЬТЕ СУММЫ'),
 ('text-held',{M:dict(D9='текст')},'ПРОВЕРЬТЕ СУММЫ'),
 ('text-return',{M:dict(E9='текст')},'ПРОВЕРЬТЕ СУММЫ'),
 ('boolean-held',{M:dict(D9=True)},'ПРОВЕРЬТЕ СУММЫ'),
 ('fractional-kopeck',{M:dict(E9=20000.001)},'ПРОВЕРЬТЕ СУММЫ'),
 ('missing-return-not-zero',{M:dict(E9=None)},'ПРОВЕРЬТЕ СУММЫ'),
 ('missing-other-not-zero',{M:dict(F9=None)},'ПРОВЕРЬТЕ СУММЫ'),
 ('missing-act',{M:dict(B9=None)},'УКАЖИТЕ АКТ'),
 ('held-exceeds-act',{M:dict(C9=90000)},'УДЕРЖАНО > АКТА'),
 ('over-return',{M:dict(E9=120000)},'ПОГАШЕНО > УДЕРЖАНО'),
 ('combined-over-discharge',{M:dict(F9=90000),T:dict(M9=sn('2026-10-18'))},'ПОГАШЕНО > УДЕРЖАНО'),
 ('missing-cash-date',{T:dict(J9=None)},'ВОЗВРАТ: ДАННЫЕ'),
 ('cash-date-future',{T:dict(J9=sn('2026-10-24'))},'ВОЗВРАТ: ДАННЫЕ'),
 ('missing-cash-proof',{T:dict(K9=None)},'ВОЗВРАТ: ДАННЫЕ'),
 ('missing-other-date',{M:dict(F9=10000)},'ПОГАШЕНИЕ: ДАННЫЕ'),
 ('other-date-future',{M:dict(F9=10000),T:dict(M9=sn('2026-10-24'))},'ПОГАШЕНИЕ: ДАННЫЕ'),
 ('text-calculation-date',{M:dict(B3='не дата')},'ДАТА РАСЧЁТА'),
 ('fractional-calculation-date',{M:dict(B3=sn('2026-10-23')+.5)},'ДАТА РАСЧЁТА')]:case(name,ch,dict(G9=msg,G5='ПРОВЕРЬТЕ РЕЕСТР',H5='ПРОВЕРЬТЕ УСЛОВИЯ'))
case('zero-retention',{M:dict(D9=0,E9=0,F9=0),T:dict(I9=None,J9=None,K9=None)},dict(G9=0,H9=0,G5=0,H5=0,I9='УДЕРЖАНИЯ НЕТ'))
case('kopeck-precision',{M:dict(D9=100.01,E9=20.02)},dict(G9=79.99,H9=79.99,G5=79.99,H5=79.99))
# Preserve all twelve records; no five-row reduction and no silent omission.
def at_row(src,r):
 dst={M:{},T:{}}
 for s,cs in src.items():
  for a,v in cs.items():
   if a=='B3'and s==M:dst[s][a]=v
   else:dst[s][a[:-1]+str(r)]=v
 return dst
data=at_row(base,20);case('twelfth-record',original=data,expected=dict(G20=80000,H20=80000,G5=80000,H5=80000,I5=1))
two=copy.deepcopy(base)
for s,cs in at_row(base,10).items():two[s].update(cs)
two[M]['B10']='КС-2 №2 от 16.10.2025';two[M].update(D10=50000,E10=0);two[T]['G10']=sn('2026-10-30');two[T].pop('J10',None)
case('mixed-due-and-future-records',original=two,expected=dict(G5=130000,H5=80000,G10=50000,H10=0,I5=2))
two[M]['B10']=base[M]['B9'];case('duplicate-act-blocked',original=two,expected=dict(G9='ПОВТОР АКТА',G10='ПОВТОР АКТА',G5='ПРОВЕРЬТЕ РЕЕСТР',H5='ПРОВЕРЬТЕ УСЛОВИЯ'))
allrows={M:{'B3':base[M]['B3']},T:{}}
for r in range(9,21):
 for s,cs in at_row(base,r).items():allrows[s].update(cs)
 allrows[M]['B'+str(r)]='КС-2 №'+str(r-8)+' от 15.10.2025'
case('all-twelve-records',original=allrows,expected=dict(D5=1200000,E5=240000,F5=0,G5=960000,H5=960000,I5=12))
case('empty-template',original={},expected=dict(G9='',H9='',G5='НЕТ ДАННЫХ',H5='НЕТ ДАННЫХ',I5='НЕТ ДАННЫХ'))
assert len({x['name']for x in cases})==len(cases)
(O/'CASES.json').write_text(json.dumps(dict(main_sheet=M,terms_sheet=T,cases=cases),ensure_ascii=False,indent=2)+'\n');print(len(cases),'independent cases')
