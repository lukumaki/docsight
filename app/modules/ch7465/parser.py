"""Strict offline parser for CH7465 native Network Log XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET

MAX_XML_BYTES = 1024 * 1024
_FIELDS = ("prior", "text", "time", "t")


def parse_network_log(xml_bytes: bytes) -> list[dict[str, str]]:
    if not isinstance(xml_bytes, bytes) or len(xml_bytes) > MAX_XML_BYTES:
        raise ValueError("Invalid Network Log response size")
    upper = xml_bytes.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("Unsupported Network Log XML declaration")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("Malformed Network Log XML") from None
    if root.tag != "eventlog_table":
        raise ValueError("Unexpected Network Log XML root")
    rows = []
    for category in ("eventlog", "wifieventlog"):
        for node in root.findall(category):
            row = {"category": category}
            for field in _FIELDS:
                child = node.find(field)
                row[field] = "" if child is None or child.text is None else child.text
            rows.append(row)
    if any(child.tag not in {"eventlog", "wifieventlog"} for child in root):
        raise ValueError("Unexpected Network Log XML element")
    return rows
