from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

XML_NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
CELL_REF_RE = re.compile(r"([A-Z]+)(\d+)")


def read_xlsx(path: str | Path) -> dict[str, list[list[str | None]]]:
    workbook_path = Path(path)
    with ZipFile(workbook_path) as archive:
        shared_strings = _load_shared_strings(archive)
        sheet_targets = _load_sheet_targets(archive)
        sheets: dict[str, list[list[str | None]]] = {}

        for name, target in sheet_targets.items():
            xml_path = target if target.startswith("xl/") else f"xl/{target}"
            sheets[name] = _parse_sheet_rows(archive.read(xml_path), shared_strings)

        return sheets


def _load_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("main:si", XML_NS):
        values.append("".join(text.text or "" for text in item.iterfind(".//main:t", XML_NS)))
    return values


def _load_sheet_targets(archive: ZipFile) -> dict[str, str]:
    workbook_xml = ET.fromstring(archive.read("xl/workbook.xml"))
    rels_xml = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationships = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels_xml.findall("pkgrel:Relationship", XML_NS)
    }

    targets: dict[str, str] = {}
    sheets = workbook_xml.find("main:sheets", XML_NS)
    if sheets is None:
        return targets

    rel_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    for sheet in sheets:
        name = sheet.attrib["name"]
        targets[name] = relationships[sheet.attrib[rel_key]]
    return targets


def _parse_sheet_rows(xml_bytes: bytes, shared_strings: list[str]) -> list[list[str | None]]:
    sheet = ET.fromstring(xml_bytes)
    sheet_data = sheet.find("main:sheetData", XML_NS)
    if sheet_data is None:
        return []

    rows: list[list[str | None]] = []
    for row in sheet_data.findall("main:row", XML_NS):
        row_values: list[str | None] = []
        for cell in row.findall("main:c", XML_NS):
            ref = cell.attrib.get("r", "")
            match = CELL_REF_RE.match(ref)
            if not match:
                continue

            col_letters, _ = match.groups()
            col_index = _column_index(col_letters)
            while len(row_values) <= col_index:
                row_values.append(None)

            row_values[col_index] = _cell_value(cell, shared_strings)
        rows.append(row_values)

    return rows


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("main:v", XML_NS)
    if value_node is not None:
        raw = value_node.text
        if raw is None:
            return None
        if cell_type == "s":
            return shared_strings[int(raw)]
        return raw

    inline = cell.find("main:is", XML_NS)
    if inline is None:
        return None
    text_chunks = [node.text or "" for node in inline.iterfind(".//main:t", XML_NS)]
    return "".join(text_chunks)


def _column_index(column_letters: str) -> int:
    value = 0
    for char in column_letters:
        value = (value * 26) + (ord(char) - ord("A") + 1)
    return value - 1

