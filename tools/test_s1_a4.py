from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import pytest
ROOT = Path(__file__).resolve().parent / "candidates" / "s1-oplata-za-raboty"
@pytest.mark.parametrize("name", ["06-uvedomlenie-o-prosrochke.docx", "07-otpravka-i-dokazatelstvo.docx", "10-obrashchenie-v-sud.docx"])
def test_outgoing_paper_is_a4(name):
    with zipfile.ZipFile(ROOT / name) as z:
        xml = ET.fromstring(z.read("word/document.xml"))
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    pages = xml.findall(".//{" + ns + "}pgSz")
    assert pages
    for page in pages:
        assert page.attrib["{" + ns + "}w"] == "11906"
        assert page.attrib["{" + ns + "}h"] == "16838"
