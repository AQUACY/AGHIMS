"""
Parse a GHIMS "Dispense Statistics By Drug" export.

The download is an HTML document with an .xls extension. Rows are grouped
under a payer (SELF, NHIS, ...) and a scheme name.
"""
from __future__ import annotations

import re
from datetime import datetime
from html.parser import HTMLParser
from typing import Optional


_RANGE = re.compile(
    r"From\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+to\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
    re.I,
)


class DispenseReportError(ValueError):
    pass


def _parse_date(value: str):
    return datetime.strptime(value.strip(), "%d %b %Y").date()


class _ReportParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events = []
        self._div_class = None
        self._buf = ""
        self._capture_div = False
        self._in_row = False
        self._in_cell = False
        self._row = []
        self._bold = False
        self._bold_buf = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            cls = attrs.get("class") or ""
            if cls in {"topic", "insuranceGroup", "insuranceScheme"}:
                self._div_class = cls
                self._capture_div = True
                self._buf = ""
        elif tag == "b":
            self._bold = True
            self._bold_buf = ""
        elif tag == "tr" and "billRow" in (attrs.get("class") or ""):
            self._in_row = True
            self._row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._buf = ""

    def handle_endtag(self, tag):
        if tag == "div" and self._capture_div:
            text = " ".join(self._buf.split())
            if text:
                self.events.append(("div", self._div_class, text))
            self._capture_div = False
            self._div_class = None
        elif tag == "b" and self._bold:
            text = " ".join(self._bold_buf.split())
            if text and text.lower() != "export":
                self.events.append(("bold", text))
            self._bold = False
        elif self._in_row and tag in {"td", "th"}:
            self._row.append(" ".join(self._buf.split()))
            self._in_cell = False
            self._buf = ""
        elif tag == "tr" and self._in_row:
            if any(self._row):
                self.events.append(("row", self._row))
            self._in_row = False
            self._row = []

    def handle_data(self, data):
        if self._capture_div or self._in_cell:
            self._buf += data
        if self._bold:
            self._bold_buf += data


def parse_dispense_report(html: str) -> dict:
    if not html or "Dispense Statistics By Drug" not in html:
        raise DispenseReportError(
            "This file is not a GHIMS Dispense Statistics By Drug report."
        )
    match = _RANGE.search(html)
    if not match:
        raise DispenseReportError("The report has no From / To dates.")
    parser = _ReportParser()
    parser.feed(html)

    facility = None
    payer_group = ""
    payer_scheme = ""
    lines = []
    for event in parser.events:
        kind = event[0]
        if kind == "bold" and facility is None:
            facility = event[1]
        elif kind == "div" and event[1] == "insuranceGroup":
            payer_group = event[2]
        elif kind == "div" and event[1] == "insuranceScheme":
            payer_scheme = event[2]
        elif kind == "row":
            cells = event[1]
            if len(cells) < 4:
                continue
            drug_id, drug_name, qty_text, amount_text = cells[0], cells[1], cells[2], cells[3]
            if not drug_id or drug_id.lower() == "drug id" or drug_name.upper() == "TOTAL":
                continue
            try:
                quantity = float(str(qty_text).replace(",", ""))
                amount = float(str(amount_text).replace(",", ""))
            except ValueError:
                continue
            lines.append(
                {
                    "payer_group": payer_group,
                    "payer_scheme": payer_scheme,
                    "drug_id": drug_id.strip(),
                    "drug_name": drug_name.strip(),
                    "quantity_sold": quantity,
                    "amount": amount,
                }
            )
    if not lines:
        raise DispenseReportError("The report has no drug rows.")
    return {
        "facility_name": facility,
        "period_from": _parse_date(match.group(1)),
        "period_to": _parse_date(match.group(2)),
        "lines": lines,
    }
