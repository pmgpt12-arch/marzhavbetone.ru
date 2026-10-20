#!/usr/bin/env python3
"""Submit one bounded job to the existing Office transport without replacing active work."""
from pathlib import Path
import argparse,xml.etree.ElementTree as E,re,shutil
def previous_is_complete(root,channel):
    current=root/channel/'current.xml'
    if not current.exists():return True
    job=E.parse(current).getroot();ident=job.get('id','')
    if not re.fullmatch('[a-z0-9-]{1,64}',ident):raise ValueError('Invalid previous job ID')
    report=root/'results'/channel/ident/'report.xml'
    if not report.exists():return False
    r=E.parse(report).getroot()
    return r.get('job')==ident and r.get('status') in {'PASS','FAIL','TIMEOUT'}
def submit(root,channel,jobdir):
    if channel not in {'word','native'}:raise ValueError('Invalid channel')
    if not previous_is_complete(root,channel):raise RuntimeError('HOLD: previous receipt has not arrived; current.xml was not changed')
    job=E.parse(jobdir/'job.xml').getroot();ident=job.get('id','')
    if not re.fullmatch('[a-z0-9-]{1,64}',ident):raise ValueError('Invalid job ID')
    if not 1<=len(job.findall('file'))<=4:raise ValueError('A job contains one to four files')
    if (root/'results'/channel/ident/'report.xml').exists():raise RuntimeError('Job already has a receipt; use an immutable new ID only for a changed hypothesis')
    assert jobdir.resolve()==(root/channel/ident).resolve()
    shutil.copyfile(jobdir/'job.xml',root/channel/'current.xml')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('channel');p.add_argument('jobdir',type=Path);a=p.parse_args();submit(a.root,a.channel,a.jobdir);print('SUBMITTED',a.jobdir.name)
