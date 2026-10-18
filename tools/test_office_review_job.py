import tempfile,unittest
from pathlib import Path
from submit_office_review_job import submit
class ReceiptGate(unittest.TestCase):
 def test_pending_receipt_blocks_replacement(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);(r/'native/old').mkdir(parents=True);(r/'native/new').mkdir()
   current=r/'native/current.xml';current.write_text('<job id="old"/>');(r/'native/new/job.xml').write_text('<job id="new"><file/></job>')
   with self.assertRaisesRegex(RuntimeError,'previous receipt'):submit(r,'native',r/'native/new')
   self.assertEqual('<job id="old"/>',current.read_text())
   out=r/'results/native/old';out.mkdir(parents=True);(out/'report.xml').write_text('<report job="old" status="FAIL"/>')
   submit(r,'native',r/'native/new');self.assertIn('id="new"',current.read_text())
if __name__=='__main__':unittest.main()
