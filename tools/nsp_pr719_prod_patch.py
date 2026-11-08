#!/usr/bin/env python3
"""Only approved textual NSP product renames against current production HTML."""
import re, sys, json, pathlib, hashlib
paid={
'p1':('Система получения оплаты за выполненные работы','Получение оплаты за выполненные работы','Готовый комплект документов, расчётов и пошаговых инструкций'),
'p2':('Система оформления и получения оплаты за дополнительные работы','Оформление и оплата дополнительных работ','Документы, шаблоны и расчёты для согласования дополнительных объёмов'),
'p3':('Система подготовки и проверки документов КС-2 и КС-3 перед сдачей','Подготовка и проверка КС-2 и КС-3','Рабочий комплект форм, проверочных листов и алгоритмов сдачи'),
'p4':('Система ведения, проверки и передачи исполнительной документации','Исполнительная документация: ведение, проверка и передача','Готовые реестры, шаблоны, контрольные листы и инструкции для ПТО'),
'p5':('Система защиты подрядчика от претензий, штрафов, удержаний и зачётов','Защита от штрафов, претензий и удержаний','Комплект документов, расчётов и аргументов для защиты интересов подрядчика'),
'p7':('Система проверки и согласования договора субподряда','Проверка и согласование договора субподряда','Рабочий комплект для выявления рисков, подготовки правок и протокола разногласий'),
'p8':('Система управления авансами и расчётами по договору подряда','Авансы и расчёты по договору подряда','Документы и Excel-инструменты для проверки, учёта и возврата аванса'),
'p9':('Система защиты требований подрядчика при банкротстве генподрядчика','Взыскание задолженности при банкротстве генподрядчика','Комплект документов и алгоритмов для предъявления и защиты требований кредитора'),
'p10':('Система подготовки ответа на претензию заказчика','Ответ на претензию заказчика','Готовые формы, контррасчёты и примеры мотивированных ответов'),
'p11':('Система проверки расчётов недвижимостью и уступки прав','Расчёты неденежным способом (объектами недвижимости)','Готовый комплект документов и проверочных листов для расчётов недвижимостью и уступки прав'),
'p13':('Система проверки сметной документации и выявления неоплачиваемых затрат','Проверка сметы и выявление неоплачиваемых затрат','Практический комплект для проверки сметы, расчёта затрат и согласования цены')}
free={
'Акт скрытых работ: какие работы его требуют и что в нём проверяют':'Акт скрытых работ: когда нужен и как проверить',
'КС подписаны, денег нет: первые 7 проверок':'КС подписаны, оплаты нет: 7 первых проверок',
'Допработы: как зафиксировать поручение до начала':'Дополнительные работы: как зафиксировать поручение',
'КС без возврата: проверочный лист комплекта':'КС-2 и КС-3: проверка перед сдачей',
'Гарантийное удержание: что проверить до подписи':'Гарантийное удержание: проверка условий договора',
'Договор субподряда: красные флаги до подписи':'Договор субподряда: что проверить до подписания',
'Банкротство заказчика: проверка контрагента до подписи':'Проверка заказчика на риск банкротства',
'Аванс и обеспечение: что проверить до подписи':'Аванс и обеспечение: проверка условий договора',
'Красные флаги сделки «работы за квартиры»':'Оплата недвижимостью: риски сделки',
'Исполнительная документация: проверка комплекта до передачи':'Исполнительная документация: проверка перед передачей'}

def transform(path, content):
    original=content
    for _, (old,new,_) in paid.items():
        content=content.replace(old,new)
    for old,new in free.items():
        content=content.replace(old,new)
    if path=='katalog.html':
        found=[]
        def card(m):
            c=m.group(0)
            sm=re.search(r'data-sku="(p[0-9]+)"',c)
            if not sm or sm.group(1) not in paid:return c
            sku=sm.group(1)
            assert sku not in found, ('duplicate sku',sku)
            found.append(sku)
            name,sub=paid[sku][1:]
            c,n=re.subn(r'(<h3><a [^>]*>).*?(</a></h3>)',lambda x:x.group(1)+name+x.group(2),c,count=1,flags=re.S)
            assert n==1,('missing heading',sku)
            if 'class="product-subtitle"' not in c:
                c=c.replace('</h3>','</h3><p class="product-subtitle">'+sub+'</p>',1)
            c=re.sub(r'data-product="[^"]*"(?= data-sku="'+sku+'")',lambda _: 'data-product="'+name+'"',c)
            return c
        content=re.sub(r'<article class="product-card"[^>]*>.*?</article>',card,content,flags=re.S)
        assert set(found)==set(paid),('paid cards',found)
        assert 'data-sku="t2"' not in content and 'data-sku="t3"' not in content,'retired SKU present'
        for _,name in free.items():assert name in content,('free catalog',name)
    for sku,(_,name,sub) in paid.items():
        if path.startswith('products/'+sku+'-'):
            content,n=re.subn(r'<h1>[^<]*</h1>',lambda _: '<h1>'+name+'</h1>',content,count=1)
            assert n==1,('missing h1',path)
            content=re.sub(r'(<meta property="og:title" content=")[^"]*',lambda m:m.group(1)+name,content,count=1)
            content=re.sub(r'<title>[^<]*</title>',lambda m:'<title>'+name+' — '+('17 900 ₽' if sku in ('p3','p10','p13') else '29 900 ₽' if sku in ('p1','p5') else '24 900 ₽')+'</title>',content,count=1)
            content=re.sub(r'data-product="[^"]*"(?= data-sku="'+sku+'")',lambda _: 'data-product="'+name+'"',content)
            # Narrow JSON-LD name replacement if original did not use approved initial label.
            content=re.sub(r'("@type"\s*:\s*"Product"\s*,\s*"name"\s*:\s*")[^"]*',lambda m:m.group(1)+name,content,count=1)
            if 'class="product-subtitle"' not in content:
                content=content.replace('</h1>','</h1><p class="product-subtitle">'+sub+'</p>',1)
            assert content.count('class="product-subtitle"')==1,('subtitle count',path)
    return content

if __name__=='__main__':
    path=sys.argv[1]
    src=pathlib.Path(sys.argv[2]);out=pathlib.Path(sys.argv[3]);before=src.read_text(encoding='utf-8')
    after=transform(path,before)
    if path=='katalog.html':print('CATALOG_MATCHED',len(paid),len(free))
    out.write_text(after,encoding='utf-8')
    print(json.dumps({'path':path,'changed':after!=before,'before_sha':hashlib.sha256(before.encode()).hexdigest(),'after_sha':hashlib.sha256(after.encode()).hexdigest()},ensure_ascii=False))
