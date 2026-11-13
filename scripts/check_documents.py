"""Validate the project documentation using only the Python standard library."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = [
    "1. Background",
    "2. Work objectives",
    "3. Technical requirements",
    "4. STRIDE threat analysis",
    "5. Unit tests",
    "6. Summary and conclusions",
    "7. Architecture - UML",
    "8. Work plan",
]


def main() -> int:
    issues = []
    paths = [ROOT / name for name in ("README.md", "AGENTS.md", ".gitignore", ".gitattributes")]
    for directory in ("docs", "scripts", ".github"):
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file()
                     and "__pycache__" not in path.parts)
    for path in paths:
        name = path.relative_to(ROOT).as_posix()
        if not path.is_file():
            issues.append(f"Missing file: {name}")
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeError:
            issues.append(f"Expected UTF-8 text: {name}")
            continue
        if re.search(r"[\u0590-\u05ff\ufb1d-\ufb4f]", name + source):
            issues.append(f"Expected English project content: {name}")
        if path.suffix == ".svg":
            try:
                drawing = ET.fromstring(source)
                if drawing.tag != "{http://www.w3.org/2000/svg}svg":
                    issues.append(f"Not an SVG document: {name}")
                if not drawing.findtext("{http://www.w3.org/2000/svg}title"):
                    issues.append(f"Missing diagram title: {name}")
            except ET.ParseError as error:
                issues.append(f"Invalid SVG: {name}: {error}")
        if path.suffix != ".md":
            continue
        width = None
        in_fence = False
        for number, line in enumerate(source.splitlines(), 1):
            if line.startswith(("```", "~~~")):
                in_fence = not in_fence
            if in_fence:
                continue
            if line.startswith("|"):
                count = len(re.split(r"(?<!\\)\|", line.strip().strip("|")))
                if width is not None and count != width:
                    issues.append(f"Table columns disagree: {name}:{number}")
                width = count
            else:
                width = None
            for link in re.findall(r"!?\[[^]]*\]\(([^)]+)\)", line):
                target = urlsplit(link)
                if target.scheme or target.netloc or not target.path:
                    continue
                destination = (path.parent / unquote(target.path)).resolve()
                if not destination.is_relative_to(ROOT) or not destination.is_file():
                    issues.append(f"Missing or external local link: {name}:{number}: {link}")
        if in_fence:
            issues.append(f"Unclosed code fence: {name}")
    book_path = ROOT / "docs/project-book.md"
    if not book_path.is_file():
        issues.append("Missing project book")
    else:
        book = book_path.read_text(encoding="utf-8")
        if re.findall(r"^## (.+)$", book, re.MULTILINE) != CHAPTERS:
            issues.append("Project book must contain the eight required chapters in order")
        if len(re.findall(r"!\[[^]]*\]\(diagrams/[^)]+\.svg\)", book)) != 2:
            issues.append("Project book must reference its two UML diagrams")
    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 1
    print(f"Documentation checks passed: {len(paths)} English UTF-8 files, local links, "
          "table structure, eight chapters and two UML diagrams.")
    print("Application implementation and model experiments are pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
