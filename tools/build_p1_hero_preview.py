#!/usr/bin/env python3
"""Build a P1 visual proof from actual accepted buyer documents (no personal data)."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from docx import Document

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "products-storage/01-zakrytie-rabot"
OUT = ROOT / "assets/p1-komplekt-preview.webp"
SOURCES = ("01-ks-2.docx", "08-reestr-peredachi.xlsx", "14-raschet-procentov-395-gk.xlsx")
GOLD, DARK, DARK2, WHITE, PAPER = "#B69B65", "#292D30", "#53585C", "#FFFFFF", "#F5F4F0"
XML = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

def wb_text(path: Path) -> list[str]:
    """Only real titles/labels, never entered values or formulas."""
    with ZipFile(path) as z:
        ss = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            ss = ["".join(x.itertext()) for x in root.findall("m:si", XML)]
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        out = []
        for row in root.findall("m:sheetData/m:row", XML)[:11]:
            for c in list(row):
                if c.tag != "{"+XML["m"]+"}c" or c.find("m:f", XML) is not None:
                    continue
                v = c.find("m:v", XML)
                inline = c.find("m:is", XML)
                text = ss[int(v.text)] if c.attrib.get("t") == "s" and v is not None else (
                    v.text if v is not None and c.attrib.get("t") == "str" else
                    "".join(inline.itertext()) if inline is not None else "")
                if text and str(text).strip():
                    out.append(re.sub(r"\s+", " ", str(text)).strip())
        return out

def font(size: int, bold=False):
    folder = "/usr/share/fonts/truetype/dejavu/"
    return ImageFont.truetype(folder + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), size)

def draw_fit(draw, xy, message, size, fill, maxwidth, bold=False, minsize=20):
    message = re.sub(r"\{\{[^}]*\}\}|\[[^]]*\]", "_______", message)
    message = re.sub(r"\s+", " ", message).strip()
    while size > minsize and draw.textbbox((0,0),message,font=font(size,bold))[2] > maxwidth:
        size -= 1
    if draw.textbbox((0,0),message,font=font(size,bold))[2] > maxwidth:
        while message and draw.textbbox((0,0),message+"…",font=font(size,bold))[2] > maxwidth:
            message = message[:-1]
        message += "…"
    draw.text(xy,message,font=font(size,bold),fill=fill)
    return message

def generate() -> dict:
    hashes = {name: hashlib.sha256((SRC/name).read_bytes()).hexdigest() for name in SOURCES}
    paragraphs = [p.text.strip() for p in Document(SRC/SOURCES[0]).paragraphs if p.text.strip()]
    registry = wb_text(SRC/SOURCES[1])
    calc = wb_text(SRC/SOURCES[2])
    if not (paragraphs and "КС-2" in " ".join(paragraphs[:3]) and
            registry and "реестр" in registry[0].lower() and
            calc and "процент" in calc[0].lower()):
        raise RuntimeError("Buyer-source evidence missing; do not generate invented preview")
    im = Image.new("RGB",(1600,900),PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0,0,1600,18),fill=GOLD)
    d.text((145,65),"МАРЖА В БЕТОНЕ",font=font(31,True),fill=DARK)
    d.rounded_rectangle((1250,54,1453,108),radius=8,fill=WHITE,outline=GOLD,width=3)
    d.text((1281,64),"СИСТЕМА P1",font=font(25,True),fill=DARK)
    d.text((145,158),"Закрытие работ и получение оплаты",font=font(55,True),fill=DARK)
    d.text((147,235),"Фрагменты рабочих документов из комплекта",font=font(32),fill=DARK2)
    d.line((145,306,1454,306),fill=GOLD,width=5)

    groups=[
        ("01 / ФОРМА", paragraphs[0], [paragraphs[1] if len(paragraphs)>1 else "КС-2",
            "Реквизиты сторон и объекта", "Основание и объём работ"]),
        ("02 / РЕЕСТР", registry[0], registry[2:5] if len(registry)>3 else registry[1:]),
        ("03 / РАСЧЁТ", calc[0], calc[2:6] if len(calc)>3 else calc[1:]),
    ]
    boxes=[(145,365,555,795),(595,365,1005,795),(1045,365,1455,795)]
    for (tag,title,lines),(x1,y1,x2,y2) in zip(groups,boxes):
        d.rounded_rectangle((x1,y1,x2,y2),radius=14,fill=WHITE,outline="#D7D7D2",width=2)
        d.rectangle((x1+1,y1+1,x2-1,y1+11),fill=GOLD)
        d.text((x1+28,y1+37),tag,font=font(27,True),fill="#8C754A")
        draw_fit(d,(x1+28,y1+105),title,34,DARK,x2-x1-56,bold=True,minsize=23)
        yy=y1+199
        for line in lines[:3]:
            if not line:continue
            d.line((x1+30,yy+43,x2-30,yy+43),fill="#E7E7E2",width=2)
            draw_fit(d,(x1+29,yy),line,24,DARK2,x2-x1-58,minsize=19)
            yy+=72
    d.text((145,843),"Форма  •  Реестр  •  Расчётный инструмент",font=font(27),fill=DARK2)
    return {"source_hashes":hashes,"image":im}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--check",action="store_true");args=ap.parse_args()
    obj=generate();buf=io.BytesIO()
    obj["image"].save(buf,format="WEBP",quality=89,method=6)
    data=buf.getvalue()
    if args.check:
        if not OUT.is_file():raise SystemExit("PREVIEW_MISSING")
        with Image.open(OUT) as i:
            if i.size!=(1600,900) or i.getbbox() is None:
                raise SystemExit("PREVIEW_ZERO_OR_INVALID")
        # Inputs are never fictionalized. Exact image bytes are deterministic on pinned toolchain.
        if OUT.read_bytes()!=data:raise SystemExit("PREVIEW_STALE_OR_MISMATCH")
        print("P1_PREVIEW_CHECK_PASS",hashlib.sha256(data).hexdigest())
    else:
        OUT.write_bytes(data)
        print(json.dumps({"image":str(OUT.relative_to(ROOT)),"bytes":len(data),
             "sha256":hashlib.sha256(data).hexdigest(),"sources":obj["source_hashes"]},
            ensure_ascii=False))
if __name__=="__main__":main()
