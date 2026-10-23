# Historical initial plan generator; current plans/*.json are authoritative. Do not run over current candidates.
from pathlib import Path
import json,hashlib
Q=Path(__file__).resolve().parents[1]; R=Q.parent/'next-corrections/products-storage'
books=json.loads((Q/'workbook-cells.json').read_text()); plans=[]
def begin(prefix,sku,issue):
 global p
 key=next(k for k in books if k.startswith(prefix));p={'path':key,'sku':sku,'issue':issue,'base_sha256':hashlib.sha256((R/key).read_bytes()).hexdigest(),'edits':[]};plans.append(p)
def put(sh,a,value):p['edits'].append({'sheet':sh,'cell':a,'old':books[p['path']][sh].get(a),'value':value})
begin('11-bankrotstvo-genpodryadchika/04','P9','P9-04-document-sums-and-completeness')
put('Итоги','A8','Сумма значений документов в пакете, руб.')
put('Итоги','C8','Не размер долга: КС-2 и КС-3 на одни работы по 100 000 дают здесь 200 000. Долг в этом примере 100 000 до оплат. Не складывайте повторные подтверждения.')
put('Итоги','C6','Группировка по датам документов, а не готовая реестровая часть долга')
put('Итоги','C7','Дата документа сама по себе не определяет текущий платёж. Проверьте возникновение обязательства.')
put('Итоги','A18','Статья 5 п. 1–2 Закона №127-ФЗ: квалификация зависит от возникновения обязательства, а не только даты КС. Модель не решает вопрос за суд. Основание и процедуру сверяйте с файлами 02, 05, 08, 09.')
put('Реестр документов','L3','Дата документа / принятие заявления')
for n in range(4,204):
 old=books[p['path']]['Реестр документов'][f'M{n}'][1:]
 guard=f'OR($C{n}="",NOT(ISNUMBER($D{n})),$D{n}<=0,$D{n}<>INT($D{n}),AND($K{n}<>"да",$K{n}<>"нет"))'
 put('Реестр документов',f'M{n}',f'=IF($B{n}="",IF(COUNTA($C{n}:$K{n})>0,"НЕ ЗАВЕРШЕНО: укажите тип документа",""),IF({guard},"НЕ ЗАВЕРШЕНО: реквизиты, дата или включение копии",IF(AND($G{n}<>"",OR(NOT(ISNUMBER($G{n})),$H{n}="",$I{n}="")),"НЕ ЗАВЕРШЕНО: направление и подтверждение",{old})))')
begin('07-uderzhaniya-shtrafy-zachety/22','P5','P5-22-open-position-date-ties')
put('Сводка','A12','Положительный остаток: даты по возрастанию, одна строка на дату. При совпадении — первая открытая позиция в реестре. Статус «возвращено» при остатке требует сверки.')
H="'Реестр'!$H$7:$H$156";M="'Реестр'!$M$7:$M$156";A="'Реестр'!$A$7:$A$156"
for n in range(13,18):
 prev='0' if n==13 else f'$A{n-1}'
 put('Сводка',f'A{n}',f'=IFERROR(AGGREGATE(15,6,{H}/(({H}>{prev})*({M}>0)*({A}<>"")),1),"")')
 for col,target in [('B','A'),('C','B')]:
  put('Сводка',f'{col}{n}',f'=IF($A{n}="","",IFERROR(INDEX(\'Реестр\'!${target}$7:${target}$156,MATCH(1,INDEX(({H}=$A{n})*({M}>0)*({A}<>""),0),0)),""))')
put('Сводка','D4','=IF(SUMPRODUCT((\'Реестр\'!$I$7:$I$156="возвращено")*(\'Реестр\'!$M$7:$M$156>0))+COUNTIF(\'Реестр\'!$M$7:$M$156,"<0")>0,"ОШИБКА: статус возврата или превышение возврата. Сверьте реестр.","Сумма остатков; проверьте неполные исходные данные")')
begin('07-uderzhaniya-shtrafy-zachety/23','P5','P5-23-unknown-is-not-ready')
put('Сводка','A5','Введите точный КС из реестра. НЕТ ДАННЫХ — КС отсутствует; НЕ ПРОВЕРЕНО — неизвестно, блокирует ли документ закрытие. Нулевой счётчик не подтверждает полноту комплекта.')
for n in range(8,20):
 D="'Реестр'!$D$7:$D$156";K="'Реестр'!$K$7:$K$156"
 put('Сводка',f'C{n}',f'=IF($A{n}="","НЕТ ДАННЫХ",IF(COUNTIF({D},$A{n})=0,"НЕТ ДАННЫХ",IF(SUMPRODUCT(({D}=$A{n})*({K}<>"да")*({K}<>"нет"))>0,"НЕ ПРОВЕРЕНО",IF($B{n}=0,"По внесённым строкам блокирующих нет","К закрытию не готов: "&$B{n}))))')
begin('07-uderzhaniya-shtrafy-zachety/29','P5','P5-29-unknown-preserve-gaps-and-minimum')
for n in range(7,207):
 old=books[p['path']]['Опись'][f'U{n}'][1:]
 put('Опись',f'U{n}',f'=IF($B{n}="","",IF(OR(AND($G{n}<>"оригинал",$G{n}<>"копия",$G{n}<>"скан",$G{n}<>"нет"),AND($J{n}<>"да",$J{n}<>"нет")),"НЕ ПРОВЕРЕНО: наличие или обязательность",IF(AND($N{n}="да",OR($O{n}="",$M{n}="")),"передан без следа: эксперт или дата",IF(AND($P{n}="да",$Q{n}=""),"НЕ ПРОВЕРЕНО: дата запроса",{old}))))')
for n in range(5,61):
 if f'E{n}' in books[p['path']]['Обязательный минимум']:
  put('Обязательный минимум',f'E{n}',f'=SUMPRODUCT((\'Опись\'!$B$7:$B$206=$B{n})*((\'Опись\'!$G$7:$G$206="оригинал")+(\'Опись\'!$G$7:$G$206="копия")+(\'Опись\'!$G$7:$G$206="скан")))')
put('Сводка','A15','=IF($B$4=0,"НЕТ ДАННЫХ: заполните опись и обязательный минимум",IF(COUNTIF(\'Опись\'!$U$7:$U$206,"НЕ ПРОВЕРЕНО*")>0,"НЕ ПРОВЕРЕНО: устраните неизвестные сведения",IF(OR($B$6>0,$B$13>0),"Есть незакрытые обязательные документы или блоки минимума. Закройте дыры или направьте запрос.",IF(OR($B$8>0,$B$9>0,$B$10>0,COUNTIF(\'Опись\'!$U$7:$U$206,"передан без следа*")>0),"Проверьте запросы, получение и передачу эксперту","По внесённым сведениям минимум закрыт; сверить состав и доказательства передачи"))))')
begin('02-dopraboty-bez-poter/07','P2','P2-07-incomplete-cost')
for n in range(4,104):
 put('Реестр',f'F{n}',f'=IF(COUNTA(B{n}:E{n},G{n}:H{n})=0,"",IF(OR(B{n}="",NOT(ISNUMBER(D{n})),NOT(ISNUMBER(E{n})),D{n}<=0,E{n}<0),"НЕ ЗАВЕРШЕНО",D{n}*E{n}))')
 put('Реестр',f'I{n}',f'=IF(F{n}="","",IF(OR(NOT(ISNUMBER(F{n})),AND(H{n}<>"",OR(NOT(ISNUMBER(H{n})),H{n}<=0))),"НЕ ЗАВЕРШЕНО",F{n}*IF(H{n}="",1,H{n})))')
put('Реестр','H104','=IF(COUNTIF(I4:I103,"НЕ ЗАВЕРШЕНО")>0,"Предварительно. Неполных строк: "&COUNTIF(I4:I103,"НЕ ЗАВЕРШЕНО"),"Итого")')
begin('08-pto-bez-zamechaniy/06','P4','P4-06-count-real-comments')
sh=next(iter(books[p['path']]))
put(sh,'E6','=SUMPRODUCT(--(LEN(D2:D4)>0))');put(sh,'H6','=SUMPRODUCT(--(LEN(D2:D4)>0),--(G2:G4<>"Закрыто"))');put(sh,'G7','Закрыто');put(sh,'H7','=SUMPRODUCT(--(LEN(D2:D4)>0),--(G2:G4="Закрыто"))')
begin('08-pto-bez-zamechaniy/07','P4','P4-07-progress-without-empty-rows')
sh=next(iter(books[p['path']]))
put(sh,'G4','=IF(SUMPRODUCT(--(LEN(B2:B3)>0))=0,"НЕТ ДАННЫХ",IF(SUMPRODUCT(--(LEN(B2:B3)>0),--(ISNUMBER(G2:G3)=FALSE))+SUMPRODUCT(--(LEN(B2:B3)>0),--(G2:G3<0))+SUMPRODUCT(--(LEN(B2:B3)>0),--(G2:G3>1))>0,"ПРОВЕРЬТЕ ПРОЦЕНТ",SUMPRODUCT(--(LEN(B2:B3)>0),G2:G3)/SUMPRODUCT(--(LEN(B2:B3)>0))))')
begin('14-peredacha-id-pod-podpis/03','T2','T2-03-whole-positive-leaf-count')
put('Опись','C133','=SUMPRODUCT(--((LEN(B11:B130)+LEN(C11:C130)+LEN(D11:D130)+LEN(F11:F130))>0),--(((B11:B130="")+(C11:C130="")+(D11:D130="")+(ISNUMBER(F11:F130)=FALSE)+IFERROR(--(F11:F130<=0),1)+IFERROR(--(MOD(F11:F130,1)<>0),1))>0))')
put('Опись','E132','=IF(C133>0,"ПРОВЕРЬТЕ СТРОКИ",SUM(F11:F130))');put('Опись','A133','Неполных / неверных строк')
begin('16-chto-v-smete-ne-oplatyat/63','P13','P13-63-contradictory-covered-status')
old=books[p['path']]['Реестр затрат']['C53'][1:]
bad='SUMPRODUCT((I2:I52="покрыто, проверено")*(((D2:D52<>"да")+(E2:E52="")+(G2:G52="")+(ISNUMBER(H2:H52)=FALSE)+(H2:H52<>0))>0))'
put('Реестр затрат','C53',f'=IF({bad}>0,"ПРОТИВОРЕЧИЕ: проверьте полное покрытие, позицию сметы и нулевой остаток",{old})')
put('Реестр затрат','H54','=SUMIFS(H2:H52,I2:I52,"<>принято",I2:I52,"<>не применяется")')
put('Как заполнять','B7','«Покрыто, проверено» допустимо только при полном покрытии «да», позиции сметы, документе и нулевом остатке. Непокрытый остаток учитывается даже при ошибочно закрытом статусе. «Принято» означает отдельное документированное решение о распределении расхода.')
for i,p in enumerate(plans):(Q/'plans'/f'{i+1:02}-{p["sku"]}.json').write_text(json.dumps(p,ensure_ascii=False,indent=2))
print('PLANS',len(plans),'EDITS',sum(len(p['edits'])for p in plans))
