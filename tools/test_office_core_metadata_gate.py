#!/usr/bin/env python3
"""Prevent recurrence of the native Excel double-timezone failure."""
import unittest
from io import BytesIO
from zipfile import ZipFile
from office_core_metadata_gate import check_bytes
def package(created,modified='2026-10-18T00:00:00Z'):
 b=BytesIO()
 with ZipFile(b,'w') as z:
  z.writestr('docProps/core.xml',f'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:d="http://purl.org/dc/terms/"><d:created>{created}</d:created><d:modified>{modified}</d:modified></cp:coreProperties>')
 return b.getvalue()
class Regression(unittest.TestCase):
 def test_historical_created_and_modified_failures(self):
  for created,modified in [('2000-01-01T00:00:00+00:00Z','2026-10-18T00:00:00Z'),('2000-01-01T00:00:00Z','2026-10-18T00:00:00+00:00Z')]:
   with self.subTest(created=created,modified=modified),self.assertRaisesRegex(ValueError,'invalid .* timestamp'):
    check_bytes(package(created,modified),'fixture.xlsx')
 def test_valid_utc_and_offset_dates(self):
  for value in ['2000-01-01T00:00:00Z','2026-10-18T03:00:00+03:00']:
   self.assertTrue(check_bytes(package(value),'fixture.xlsx'))
if __name__=='__main__':unittest.main()
