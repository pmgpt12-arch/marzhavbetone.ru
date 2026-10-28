#!/usr/bin/env python3
"""Read-only XLSX export gate. Preserve existing print metadata before release."""
from pathlib import Path
import argparse,hashlib,json,zipfile,xml.etree.ElementTree as E
S={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def snapshot(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, 'INVALID_ZIP_CRC'
        book=E.fromstring(z.read('xl/workbook.xml'))
        names={n.get('name')+':'+str(n.get('localSheetId')):(n.text or '') for n in book.findall('s:definedNames/s:definedName',S) if n.get('name','').startswith('_xlnm.Print')}
        pages={}
        for name in z.namelist():
            if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                root=E.fromstring(z.read(name));items={}
                for tag in ('pageSetup','pageMargins','printOptions','headerFooter'):
                    el=root.find('s:'+tag,S)
                    items[tag]=None if el is None else {'attributes':dict(el.attrib),'text':''.join(el.itertext())}
                setup=root.find('s:sheetPr/s:pageSetUpPr',S)
                items['pageSetUpPr']=None if setup is None else dict(setup.attrib)
                pages[name]=items
    return {'print_names':names,'sheet_print_metadata':pages}
def compare(before,after):
    errors=[]
    for key,value in before['print_names'].items():
        if after['print_names'].get(key)!=value:
            errors.append({'kind':'PRINT_NAME_CHANGED_OR_LOST','name':key,'before':value,'after':after['print_names'].get(key)})
    for sheet,settings in before['sheet_print_metadata'].items():
        for key,value in settings.items():
            new=after['sheet_print_metadata'].get(sheet,{}).get(key)
            if new!=value:errors.append({'kind':'PRINT_METADATA_CHANGED_OR_LOST','sheet':sheet,'setting':key,'before':value,'after':new})
    return errors
def main():
    p=argparse.ArgumentParser();p.add_argument('before',type=Path);p.add_argument('after',type=Path);p.add_argument('--json',type=Path);a=p.parse_args()
    errors=compare(snapshot(a.before),snapshot(a.after))
    r={'status':'PASS' if not errors else 'BLOCKED_PRINT_CONTRACT','before_sha256':hashlib.sha256(a.before.read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(a.after.read_bytes()).hexdigest(),'errors':errors}
    if a.json:a.json.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False));raise SystemExit(0 if not errors else 1)
if __name__=='__main__':main()
