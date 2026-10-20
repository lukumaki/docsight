"""Strict offline parser for CH7465 native Network Log XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.parsers import expat

MAX_XML_BYTES = 1024 * 1024
_FIELDS = ("prior", "text", "time", "t")


class _ForbiddenXMLDeclaration(Exception):
    """Raised when the Network Log contains a DTD or entity declaration."""


def _validate_xml_declarations(xml_bytes: bytes) -> None:
    """Parse with Expat first so declarations are detected across XML encodings."""
    parser = expat.ParserCreate()

    def reject_declaration(*_args):
        raise _ForbiddenXMLDeclaration

    parser.StartDoctypeDeclHandler = reject_declaration
    parser.EntityDeclHandler = reject_declaration
    parser.ExternalEntityRefHandler = reject_declaration
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:
        parser.Parse(xml_bytes, True)
    except _ForbiddenXMLDeclaration:
        raise ValueError("Unsupported Network Log XML declaration") from None
    except expat.ExpatError:
        raise ValueError("Malformed Network Log XML") from None


def parse_network_log(xml_bytes: bytes) -> list[dict[str, str]]:
    if not isinstance(xml_bytes, bytes) or len(xml_bytes) > MAX_XML_BYTES:
        raise ValueError("Invalid Network Log response size")
    _validate_xml_declarations(xml_bytes)
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
