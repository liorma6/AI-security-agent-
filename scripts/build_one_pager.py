"""Fill the supplied course Word template while preserving its native text boxes."""

import argparse
import base64
import html
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree as ET

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--template", type=Path, required=True)
parser.add_argument("--output", type=Path, default=ROOT / "outputs")
parser.add_argument("--private-profile", type=Path)
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
profile = json.loads((ROOT / "docs/project-profile.json").read_text(encoding="utf-8"))
private = (
    json.loads(args.private_profile.read_text(encoding="utf-8")) if args.private_profile else {}
)
ids = private.get("student_ids", {})
source = (ROOT / "docs/one-pager.md").read_text(encoding="utf-8")
sections = {}
for block in re.split(r"^## ", source, flags=re.M)[1:]:
    title, body = block.split("\n", 1)
    sections[title.strip()] = body.split("\nRepository:", 1)[0].strip()
ns = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
}


def tag(name):
    prefix, local = name.split(":")
    return "{" + ns[prefix] + "}" + local


def paragraph(text, size=10, bold=False, align="left"):
    p = ET.Element(tag("w:p"))
    pp = ET.SubElement(p, tag("w:pPr"))
    ET.SubElement(pp, tag("w:jc")).set(tag("w:val"), align)
    spacing = ET.SubElement(pp, tag("w:spacing"))
    for key, value in {"before": "0", "after": "20", "line": "220", "lineRule": "auto"}.items():
        spacing.set(tag("w:" + key), value)
    r = ET.SubElement(p, tag("w:r"))
    rp = ET.SubElement(r, tag("w:rPr"))
    fonts = ET.SubElement(rp, tag("w:rFonts"))
    for key in ["ascii", "hAnsi", "eastAsia", "cs"]:
        fonts.set(tag("w:" + key), "Calibri")
    ET.SubElement(rp, tag("w:sz")).set(tag("w:val"), str(round(size * 2)))
    ET.SubElement(rp, tag("w:szCs")).set(tag("w:val"), str(round(size * 2)))
    if bold:
        ET.SubElement(rp, tag("w:b"))
    ET.SubElement(r, tag("w:t")).text = text
    return p


team = [
    ("Team members", 11, True),
    ("Lior Mashaich", 10, True),
    ("ID: " + ids.get("Lior Mashaich", "pending"), 9, False),
    ("Sharon Elimelech", 10, True),
    ("ID: " + ids.get("Sharon Elimelech", "pending"), 9, False),
    ("Supervisor", 10, True),
    (profile["supervisor"], 10, False),
    ("Project coordination", 10, True),
    ("Lior Mashaich and Sharon Elimelech", 9, False),
    (profile["course"], 9, False),
]


def slot(original):
    original = " ".join(original.split())
    if original.startswith("Project name"):
        return "identity", [("PhishGuard", 22, True), ("HIT | AB- Ai Security", 11, False)]
    if original.startswith("The details"):
        return "team", team
    if original == "Logo":
        return "logo", [("PhishGuard", 14, True)]
    assert original in sections, original
    return original, [(original, 12, True), (sections[original], 10, False)]


with ZipFile(args.template) as archive:
    parts = {name: archive.read(name) for name in archive.namelist()}
root = ET.fromstring(parts["word/document.xml"])
anchors = root.findall(".//wp:anchor", ns)
assert len(anchors) == 13
boxes = []
for anchor in anchors:
    content = anchor.find(".//w:txbxContent", ns)
    original = "".join(content.xpath(".//w:t/text()", namespaces=ns))
    key, lines = slot(original)
    x = 3.175 + int(anchor.findtext("wp:positionH/wp:posOffset", namespaces=ns)) / 360000
    y = 2.54 + int(anchor.findtext("wp:positionV/wp:posOffset", namespaces=ns)) / 360000
    extent = anchor.find("wp:extent", ns)
    boxes.append((key, x, y, int(extent.get("cx")) / 360000, int(extent.get("cy")) / 360000, lines))
for content in root.findall(".//w:txbxContent", ns):
    original = "".join(content.xpath(".//w:t/text()", namespaces=ns))
    key, lines = slot(original)
    for child in list(content):
        content.remove(child)
    for index, (text, size, bold) in enumerate(lines):
        align = (
            "center" if key in ["identity", "logo"] or (index == 0 and key != "team") else "left"
        )
        content.append(paragraph(text, size, bold, align))
parts["word/document.xml"] = ET.tostring(
    root, xml_declaration=True, encoding="UTF-8", standalone=True
)
for name, data in list(parts.items()):
    if not name.endswith(".xml"):
        continue
    tree = ET.fromstring(data)
    for fonts in tree.findall(".//w:rFonts", ns):
        fonts.attrib.clear()
        for key in ["ascii", "hAnsi", "eastAsia", "cs"]:
            fonts.set(tag("w:" + key), "Calibri")
    for element in tree.iter():
        for key, value in list(element.attrib.items()):
            if re.search(r"[\u0590-\u05ff]", value):
                element.set(key, "Template shape")
    if name.startswith("word/footer"):
        for child in list(tree):
            tree.remove(child)
        tree.append(paragraph("HIT | AB- Ai Security | November 17, 2026", 8, align="center"))
        tree.append(paragraph("github.com/liorma6/AI-security-agent-", 8, align="center"))
    if name == "docProps/core.xml":
        mapping = {
            "title": "PhishGuard - One Pager",
            "creator": "Lior Mashaich and Sharon Elimelech",
            "lastModifiedBy": "Lior Mashaich and Sharon Elimelech",
            "subject": "HIT; AB- Ai Security; Supervisor: Zimon Roi",
        }
        for element in tree:
            key = ET.QName(element).localname
            if key in mapping:
                element.text = mapping[key]
    parts[name] = ET.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
with ZipFile(out / "PhishGuard-One-Pager.docx", "w", ZIP_DEFLATED) as archive:
    for name, data in parts.items():
        archive.writestr(name, data)
logo = base64.b64encode(parts["word/media/image1.png"]).decode()
body = [
    f'<img class="hit" src="data:image/png;base64,{logo}" alt="Supplied HIT institutional artwork">'
]
for key, x, y, width, height, lines in boxes:
    paragraphs = []
    for i, (value, size, bold) in enumerate(lines):
        centered = key in ["identity", "logo"] or (i == 0 and key != "team")
        alignment = "center" if centered else "left"
        paragraphs.append(
            f'<p style="font-size:{size}pt;font-weight:{700 if bold else 400};'
            f'text-align:{alignment}">{html.escape(value)}</p>'
        )
    text = "".join(paragraphs)
    body.append(
        f'<section data-slot="{html.escape(key)}" style="left:{x}cm;top:{y}cm;'
        f'width:{width}cm;height:{height}cm">{text}</section>'
    )
css = (
    "@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;back"
    "ground:white;font-family:Calibri}article{position:relative;width:"
    "21cm;height:29.7cm}section{position:absolute;border:.75pt solid b"
    "lack;padding:.127cm .254cm;overflow:hidden}p{margin:0 0 1pt;line-"
    "height:1.1}.hit{position:absolute;left:6.2cm;top:.2cm;width:8.6cm"
    ";height:auto}footer{position:absolute;top:27.6cm;left:1cm;width:1"
    "9cm;text-align:center;font-size:8pt;line-height:1.5}"
)
css += (
    ".hit{left:-.051cm;top:0;width:6.844cm;height:2.15cm}"
    ".template-heading{position:absolute;left:3.175cm;top:1.249cm;"
    "width:14.65cm;text-align:center;font-size:22pt}"
)
body.insert(0, '<div class="template-heading">One Pager</div>')
page = (
    (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Phish'
        "Guard - One Pager</title><style>"
    )
    + css
    + "</style><body><article>"
    + "".join(body)
    + (
        "<footer>HIT | AB- Ai Security | November 17, 2026<br>github.com/l"
        "iorma6/AI-security-agent-</footer></article></body></html>"
    )
)
(out / "PhishGuard-One-Pager.html").write_text(page, encoding="utf-8")
print(
    "Filled all 13 native template boxes; wrote Word and matching HTML"
    " without publishing student identifiers."
)
