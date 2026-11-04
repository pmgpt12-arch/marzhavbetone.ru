from pathlib import Path
import zipfile,json,hashlib
from lxml import etree as E
Q=Path(__file__).resolve().parents[1];P=Q/'paid-followup-20261023';src=P/'p11-layout-v2/53-zapros-status-obekta.docx';ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
changes={'Письменно установить, в каком состоянии объект на самом деле: итоговая проверка, ЗОС, разрешение на строительство, ввод. Отправляется — текст письма ниже; страница «Как пользоваться этим документом» в отправку не входит.':'Письменно установить, в каком состоянии объект на самом деле: итоговая проверка, ЗОС, разрешение на строительство, ввод. Заказчику направляется заполненная форма от «Кому:» до подписи перед разрывом страницы. Следующие пояснения покупателю не направляются.','Примечание покупателю. Эта страница в отправляемое письмо не входит: отправляется только текст до разрыва страницы.':'Примечание покупателю. Направляется заполненная форма перед разрывом страницы; все последующие пояснения покупателю в письмо не включаются.'}
with zipfile.ZipFile(src)as z:infos=z.infolist();parts={i.filename:z.read(i)for i in infos}
root=E.fromstring(parts['word/document.xml'])
for a,b in changes.items():
 found=0
 for p in root.findall('.//w:p',ns):
  ts=p.findall('.//w:t',ns)
  if ''.join(t.text or ''for t in ts)==a:
   ts[0].text=b
   for t in ts[1:]:t.text=''
   found+=1
 assert found==1,(a,found)
parts['word/document.xml']=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
D=P/'p11-layout-v3';D.mkdir(exist_ok=True);dst=D/src.name
with zipfile.ZipFile(dst,'w')as z:
 for i in infos:z.writestr(i,parts[i.filename])
row=json.loads((P/'P11_LAYOUT_V2.json').read_text())[0];row['previous_sha256']=row['new_sha256'];row['new_sha256']=hashlib.sha256(dst.read_bytes()).hexdigest();row['guide_changes']=changes
(P/'P11_LAYOUT_V3.json').write_text(json.dumps([row],ensure_ascii=False,indent=2))
s=(Q/'scripts/native_p11_layout_v2.py').read_text()
for a,b in {'nsp-p11-letter-layout-v2-20261023':'nsp-p11-letter-layout-v3-20261023','P11_LAYOUT_V2.json':'P11_LAYOUT_V3.json',"'p11-layout-v2'":"'p11-layout-v3'","tag='pl'":"tag='pv'",'visual-p11-layout-v2':'visual-p11-layout-v3','P11_LAYOUT_NATIVE_V2.json':'P11_LAYOUT_NATIVE_V3.json'}.items():
 assert s.count(a)==1;s=s.replace(a,b)
(Q/'scripts/native_p11_layout_v3.py').write_text(s)
print('V3',row['new_sha256'])
