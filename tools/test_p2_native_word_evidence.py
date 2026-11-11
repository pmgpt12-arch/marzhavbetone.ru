#!/usr/bin/env python3
"""SHA-bound native Word evidence. Does not perform or claim product acceptance."""
from pathlib import Path
import copy,hashlib,json,sys,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'tools/candidates/p2-instruction-style-20261013'
SHA='0f3882fae04bd8bf32a9c368abc24e6d4c1c41fad5d008d37bfc522098148b11'
PDF='e5e61bc7d38772bd8407681a82e76794383e92426a7b85191201cad9f23aed57'
JOB='p2-instruction-style-word-20261013-v1'
def require(ok,code):
    if not ok: raise ValueError(code)
def sha(b): return hashlib.sha256(b).hexdigest()
def verify(data):
    require(sha(data['00-INSTRUKCIYA.docx'])==SHA,'INPUT_SHA_DRIFT')
    pdf=data['00-INSTRUKCIYA-native-word.pdf']
    require(pdf.startswith(b'%PDF-') and sha(pdf)==PDF,'NATIVE_PDF_DRIFT')
    job=E.fromstring(data['native-word-job.xml'])
    require(job.tag=='job' and job.get('id')==JOB and len(job.findall('file'))==1,'JOB_SCHEMA_DRIFT')
    f=job.find('file')
    require(f.get('sha256')==SHA and f.get('name')=='p2-instruction.docx' and f.get('tag')=='p2style','JOB_INPUT_DRIFT')
    report=E.fromstring(data['native-word-report.xml'])
    require(report.get('job')==JOB and report.get('status')=='PASS','NATIVE_REPORT_NOT_PASS')
    require(len(report.findall('file'))==1,'NATIVE_FILE_COUNT_DRIFT')
    f=report.find('file')
    require(f.get('tag')=='p2style' and f.get('status')=='PASS' and f.get('pdf_sha256')==PDF,'NATIVE_FILE_REPORT_DRIFT')
    v=json.loads(data['native-word-visual-review.json'])
    require(v.get('input_sha256')==SHA and v.get('native_pdf_sha256')==PDF,'VISUAL_SOURCE_DRIFT')
    require(v.get('native_report_sha256')==sha(data['native-word-report.xml']),'VISUAL_REPORT_DRIFT')
    require(v.get('status')=='PASS_NATIVE_WORD_OPEN_EXPORT_AND_VISUAL_LAYOUT_ONLY','VISUAL_SCOPE_DRIFT')
    require(v.get('pages_reviewed')==4 and v.get('format')=='A4' and v.get('visual_findings')==[],'VISUAL_NOT_ACCEPTED')
    pages=v.get('page_images',[])
    require(len(pages)==4 and {p['name'] for p in pages}=={'page-%d.png'%i for i in range(1,5)},'PAGE_REVIEW_COVERAGE')
    require(all(len(p.get('sha256',''))==64 for p in pages),'PAGE_REVIEW_HASH_MISSING')
    require(v.get('release')=='BLOCKED' and 'independent buyer G1-G8' in v.get('not_accepted',[]),'FALSE_PRODUCT_ACCEPTANCE')
    rec=json.loads(data['review-receipt.json'])
    require(rec.get('schema_version')==2 and rec.get('candidate_sha256')==SHA,'STALE_REVIEW_RECEIPT')
    require(rec.get('status')=='PASS_P2_STRUCTURAL_EDITORIAL_AND_NATIVE_WORD_LAYOUT_ONLY','RECEIPT_SCOPE_DRIFT')
    require(rec.get('office_gate')=='PASS_NATIVE_WORD_OPEN_EXPORT_AND_VISUAL_LAYOUT_ONLY','RECEIPT_OFFICE_GATE_DRIFT')
    require(rec.get('native_job_id')==JOB and rec.get('native_pdf_sha256')==PDF,'RECEIPT_NATIVE_EVIDENCE_DRIFT')
    require(rec.get('native_report_sha256')==sha(data['native-word-report.xml']),'RECEIPT_REPORT_HASH_DRIFT')
    entry=json.loads(data['entrypoint-text-qa.json'])
    require('native Word' not in entry.get('remaining',[]),'STALE_ENTRYPOINT_QA')
    require('controlled canonical instruction DOCX/PDF replacement' in entry.get('remaining',[]),'ENTRYPOINT_REPLACEMENT_GATE_MISSING')
def main():
    names=['00-INSTRUKCIYA.docx','00-INSTRUKCIYA-native-word.pdf','native-word-job.xml','native-word-report.xml','native-word-visual-review.json','review-receipt.json','entrypoint-text-qa.json']
    data={n:(D/n).read_bytes() for n in names}
    verify(data)
    negatives=[]
    for k in range(6):
        bad=copy.deepcopy(data)
        if k==0: bad['00-INSTRUKCIYA.docx']+=b'x'
        elif k==1: bad['00-INSTRUKCIYA-native-word.pdf']+=b'x'
        elif k==2: bad['native-word-job.xml']=bad['native-word-job.xml'].replace(SHA.encode(),b'0'*64)
        elif k==3: bad['native-word-report.xml']=bad['native-word-report.xml'].replace(b'status="PASS"',b'status="FAIL"',1)
        else:
            v=json.loads(bad['native-word-visual-review.json'])
            if k==4: v['pages_reviewed']=3
            else: v['not_accepted']=[];v['release']='PASS'
            bad['native-word-visual-review.json']=json.dumps(v).encode()
        try: verify(bad)
        except ValueError as e: negatives.append(str(e))
        else: raise RuntimeError('NEGATIVE_NOT_DETECTED_%d'%k)
    print('P2_NATIVE_WORD_EVIDENCE_PASS: exact DOCX/PDF/native report; 4 pages; 6/6 artifact mutations plus active-receipt gates; not legal/buyer/G1-G8')
    print(json.dumps(negatives))
if __name__=='__main__':
    try: main()
    except Exception as e: print('P2_NATIVE_WORD_EVIDENCE_FAIL: '+repr(e),file=sys.stderr);sys.exit(1)
