#!/usr/bin/env python3
"""Strict OOXML core timestamp gate, including the historical double UTC suffix."""
from zipfile import ZipFile
from lxml import etree as E
from pathlib import Path
import sys,json
SCHEMA=E.XMLSchema(E.fromstring(b'<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"><xs:element name="date" type="xs:dateTime"/></xs:schema>'))
NS={'d':'http://purl.org/dc/terms/'}
def check_bytes(data,label):
 from io import BytesIO
 with ZipFile(BytesIO(data)) as z:
  assert z.testzip() is None,(label,'CRC')
  r=E.fromstring(z.read('docProps/core.xml'))
  for field in ['created','modified']:
   e=r.find('d:'+field,NS)
   if e is None:continue
   d=E.Element('date');d.text=e.text
   if not SCHEMA.validate(d):raise ValueError(f'{label}: invalid {field} timestamp {e.text!r}')
 return True
def check(path):
 if path.suffix=='.zip':
  with ZipFile(path) as z:
   return sum(check_bytes(z.read(n),str(path)+'!'+n) for n in z.namelist() if n.endswith(('.xlsx','.docx')))
 return int(check_bytes(path.read_bytes(),str(path)))
if __name__=='__main__':
 count=sum(check(Path(p)) for p in sys.argv[1:])
 print(json.dumps({'status':'PASS','office_files':count}))
