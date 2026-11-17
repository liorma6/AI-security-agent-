"""Export the canonical English One Pager as editable Word and printable HTML."""

import argparse
import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import markdown
from docx import Document
from docx.oxml import OxmlElement
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "outputs")
args = parser.parse_args()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
source = (ROOT / "docs/one-pager.md").read_text(encoding="utf-8")
profile = json.loads((ROOT / "docs/project-profile.json").read_text(encoding="utf-8"))
fragment = markdown.markdown(source, extensions=["tables"])
root = ET.fromstring("<article>" + fragment + "</article>")
doc = Document()
doc.core_properties.title = "PhishGuard - One Pager"
doc.core_properties.author = " and ".join(profile["students"])
doc.core_properties.subject = profile["course"] + "; Supervisor: " + profile["supervisor"]
section = doc.sections[0]
section.page_width, section.page_height = Cm(21), Cm(29.7)
section.top_margin = section.bottom_margin = Cm(1.35)
section.left_margin = section.right_margin = Cm(1.5)
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(10)
normal.paragraph_format.line_spacing = 1.04
normal.paragraph_format.space_after = Pt(4)
for style, size in [("Title", 26), ("Heading 1", 11)]:
    doc.styles[style].font.name = "Calibri"
    doc.styles[style].font.size = Pt(size)
    doc.styles[style].font.color.rgb = RGBColor.from_string("12535B")
    doc.styles[style].paragraph_format.space_before = Pt(7 if style != "Title" else 0)
    doc.styles[style].paragraph_format.space_after = Pt(3)


def inline(paragraph, element):
    if element.text:
        paragraph.add_run(element.text)
    for child in element:
        if child.tag == "br":
            paragraph.add_run().add_break()
        else:
            run = paragraph.add_run("".join(child.itertext()))
            run.bold = child.tag == "strong"
            run.italic = child.tag == "em"
        if child.tail:
            paragraph.add_run(child.tail)


for element in root:
    if element.tag == "h1":
        doc.add_paragraph("".join(element.itertext()), "Title")
    elif element.tag == "h2":
        doc.add_paragraph("".join(element.itertext()), "Heading 1")
    elif element.tag == "p":
        inline(doc.add_paragraph(), element)
    elif element.tag == "ul":
        for item in element:
            paragraph = doc.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.space_after = Pt(2)
            inline(paragraph, item)
    elif element.tag == "table":
        rows = element.findall(".//tr")
        table = doc.add_table(rows=0, cols=3)
        table.style = "Light Shading Accent 1"
        for index, row in enumerate(rows):
            cells = table.add_row().cells
            for cell, item in zip(cells, row, strict=True):
                inline(cell.paragraphs[0], item)
                cell.paragraphs[0].paragraph_format.space_after = Pt(2)
                for run in cell.paragraphs[0].runs:
                    run.font.size = Pt(9)
                    run.bold = index == 0
            props = table.rows[-1]._tr.get_or_add_trPr()
            props.append(OxmlElement("w:cantSplit"))
            if index == 0:
                props.append(OxmlElement("w:tblHeader"))
        for row in table.rows:
            for cell, width in zip(row.cells, [6.2, 2.6, 9.2], strict=True):
                cell.width = Cm(width)
footer = section.footer.paragraphs[0]
footer.text = "HIT | AB- Ai Security | PhishGuard"
footer.runs[0].font.size = Pt(8)
footer.runs[0].font.color.rgb = RGBColor.from_string("4C686B")
doc.save(output / "PhishGuard-One-Pager.docx")

css = """
@page{size:A4;margin:13.5mm 15mm}*{box-sizing:border-box}
body{font:10pt/1.21 Arial,sans-serif;color:#183b40;margin:0}
h1{font-size:29pt;line-height:1;margin:0 0 5pt;color:#12535b;letter-spacing:-1px}
h2{font-size:11pt;margin:9pt 0 4pt;color:#12535b;border-bottom:1px solid #d8e6e2;
padding-bottom:3pt;break-after:avoid}p{margin:4pt 0 6pt}ul{margin:4pt 0;padding-left:15pt}
li{margin:3pt 0}table{width:100%;border-collapse:collapse;margin:7pt 0;font-size:9pt}
th,td{padding:5pt 7pt;text-align:left;border-bottom:1px solid #d9e8e4}
th{background:#12535b;color:white}tr:nth-child(even){background:#eef5f2}
tr{break-inside:avoid}article{border-top:5px solid #d99b4e;padding-top:12pt}
"""
page = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>'
    + html.escape("PhishGuard - One Pager")
    + "</title><style>"
    + css
    + "</style></head><body><article>"
    + fragment
    + "</article></body></html>"
)
(output / "PhishGuard-One-Pager.html").write_text(page, encoding="utf-8")
print("Exported editable Word and HTML from the canonical One Pager source.")
