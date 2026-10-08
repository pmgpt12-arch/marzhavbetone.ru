#!/usr/bin/env python3
"""Normalize six P1 retention-card accents; preserve all text and page count.
Run with a Python runtime containing pypdf. No deployment dependency.
"""
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

ROOT = Path(__file__).resolve().parent.parent
REL = "10-sroki-hraneniya.pdf"
BASE = ROOT / "products-storage/01-zakrytie-rabot"
MIRROR = ROOT / "products-storage/04-polnyy-komplekt-pto/01-30-bazovye-pakety/01-zakrytie-rabot"
OLD = b".909804 .364706 .133333 rg"
NEW = b".705882 .603922 .396078 rg"

def normalize(blob: bytes) -> bytes:
    reader = PdfReader(BytesIO(blob))
    count = sum(page.get_contents().get_data().count(OLD) for page in reader.pages)
    if count == 0:
        assert sum(page.get_contents().get_data().count(NEW) for page in reader.pages) == 6
        return blob
    assert count == 6, "Unexpected card: inspect before changing its colors"
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for page in writer.pages:
        stream = DecodedStreamObject()
        stream.set_data(page.get_contents().get_data().replace(OLD, NEW))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    result = PdfReader(BytesIO(output.getvalue()))
    assert len(result.pages) == len(reader.pages)
    assert [p.extract_text() for p in result.pages] == [p.extract_text() for p in reader.pages]
    return output.getvalue()

if __name__ == "__main__":
    source = BASE / REL
    result = normalize(source.read_bytes())
    source.write_bytes(result)
    (MIRROR / REL).write_bytes(result)
