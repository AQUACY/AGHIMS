"""
Parse ClaimIT import report HTML to extract claims with errors/warnings and their messages.
Supports: table#outcome-rows with tr class ERROR/WARNING. Claim IDs may be CLA-… (GHIMS XML)
or ClaimIT-native forms such as VE-0032-2601230003. Handles nested <table> inside rows
(so we use depth counting to get the full outcome-rows table and to split rows).
"""

import re
from typing import List, Dict, Any, Optional


def _find_table_content(html: str, table_id: str) -> Optional[str]:
    """Extract content of <table id='outcome-rows'>...</table> using depth count (handles nested tables)."""
    pat = re.compile(
        r"<table[^>]*id=['\"]" + re.escape(table_id) + r"['\"][^>]*>",
        re.IGNORECASE,
    )
    m = pat.search(html)
    if not m:
        return None
    start = m.end()
    depth = 1
    i = start
    while i < len(html):
        if html[i : i + 7].lower() == "<table":
            depth += 1
            i += 7
            continue
        if html[i : i + 8].lower() == "</table>":
            depth -= 1
            if depth == 0:
                return html[start:i]
            i += 8
            continue
        i += 1
    return None


def _find_tr_end(html: str, start: int) -> int:
    """Given start position after <tr...>, return index of matching </tr> (count nested <tr>/</tr>)."""
    depth = 1
    i = start
    while i < len(html) - 5:
        rest = html[i : i + 10].lower()
        if rest.startswith("<tr") and (rest[3:4] in " \t>"):
            depth += 1
            i += 3
            continue
        if html[i : i + 5].lower() == "</tr>":
            depth -= 1
            if depth == 0:
                return i
            i += 5
            continue
        i += 1
    return -1


def _extract_overview(html_content: str) -> Dict[str, Any]:
    """
    ClaimIT overview table: either a Totals row, or one or more Claim Month rows
    (e.g. <td>Dec 2025</td><td><b>39</b> passed ...).
    """
    overview: Dict[str, Any] = {}
    overview_match = re.search(
        r"<table[^>]*class=['\"]overview['\"][^>]*>.*?<tr>\s*<td>Totals</td>.*?"
        r"<td[^>]*>\s*<b>(\d+)</b>\s*</td>\s*<td[^>]*>\s*<b>(\d+)</b>\s*</td>\s*<td[^>]*>\s*<b>(\d+)</b>\s*</td>\s*<td[^>]*>\s*<b>\s*(\d+)\s*</b>",
        html_content,
        re.DOTALL | re.IGNORECASE,
    )
    if overview_match:
        overview["passed"] = int(overview_match.group(1).replace(",", ""))
        overview["warning"] = int(overview_match.group(2).replace(",", ""))
        overview["failed"] = int(overview_match.group(3).replace(",", ""))
        overview["total"] = int(overview_match.group(4).replace(",", ""))

    title_match = re.search(r"<title>ClaimIt Import Report\s*(.+?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        overview["report_date"] = title_match.group(1).strip()

    # Per–claim-month rows (common standalone export; no "Totals" row)
    if overview.get("passed") is None and overview.get("total") is None:
        tab_m = re.search(
            r"<table[^>]*class=['\"]overview['\"][^>]*>(.*?)</table>",
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        if tab_m:
            inner = tab_m.group(1)
            by_month: List[Dict[str, Any]] = []
            tp = tw = tf = 0
            for tr_m in re.finditer(r"<tr[^>]*>(.*?)</tr>", inner, re.DOTALL | re.IGNORECASE):
                tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr_m.group(1), re.IGNORECASE)
                if len(tds) < 4:
                    continue
                month_raw = re.sub(r"<[^>]+>", "", tds[0]).strip()
                if not month_raw or month_raw.lower() in ("report date", "claim month"):
                    continue
                if month_raw.lower() == "totals":
                    continue
                nums: List[int] = []
                for i in range(1, min(5, len(tds))):
                    cell = tds[i]
                    b_m = re.search(r"<b>\s*([\d,\.]+)\s*</b>", cell, re.IGNORECASE)
                    if b_m:
                        raw = b_m.group(1).replace(",", "")
                    else:
                        raw = re.sub(r"<[^>]+>", " ", cell)
                        raw = re.sub(r"\s+", " ", raw).strip().replace(",", "")
                        mnum = re.search(r"([\d.]+)", raw)
                        raw = mnum.group(1) if mnum else ""
                    if not raw:
                        nums = []
                        break
                    if "." in raw:
                        try:
                            nums.append(int(float(raw)))
                        except ValueError:
                            nums.append(0)
                    else:
                        try:
                            nums.append(int(raw))
                        except ValueError:
                            nums = []
                            break
                if len(nums) >= 3:
                    p, w, f = nums[0], nums[1], nums[2]
                    entry = {"month": month_raw, "passed": p, "warning": w, "failed": f}
                    if len(nums) > 3:
                        entry["total_volume"] = nums[3]
                    by_month.append(entry)
                    tp += p
                    tw += w
                    tf += f
            if by_month:
                overview["by_month"] = by_month
                overview["passed"] = tp
                overview["warning"] = tw
                overview["failed"] = tf
                overview["total"] = tp + tw + tf

    return overview


def _extract_claim_id_from_row(row_html: str) -> Optional[str]:
    """
    ClaimIT reports may use CLA-… (GHIMS export) or institutional IDs such as VE-0032-2601230003.
    Prefer explicit CLA-, else the Claim ID column (second <td> in the main outcome row).
    """
    m = re.search(r"\b(CLA-\d+)\b", row_html, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    tds = re.findall(r"<td[^>]*>([\s\S]*?)</td>", row_html, re.IGNORECASE)
    if len(tds) >= 2:
        candidate = re.sub(r"<[^>]+>", "", tds[1]).strip()
        if candidate and re.match(r"^[A-Za-z0-9][A-Za-z0-9.\-]{3,}$", candidate) and "-" in candidate:
            low = candidate.lower()
            if low not in ("outcome", "error", "warning", "saved", "updated"):
                return candidate

    m = re.search(r"\b([A-Z]{2,}-\d{4}-\d{6,})\b", row_html)
    if m:
        return m.group(1).strip()

    m = re.search(r"\b(CLA-[A-Z0-9.\-]+)\b", row_html, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def _extract_claim_row(row_html: str, outcome: str, row_index: int) -> Optional[Dict[str, Any]]:
    """From a single <tr>...</tr> string, extract claim_id and error_messages if present."""
    claim_id = _extract_claim_id_from_row(row_html)
    if not claim_id:
        return None

    messages: List[str] = []
    details_match = re.search(
        r"<td[^>]*class=['\"]details['\"][^>]*>(.*?)</td>",
        row_html,
        re.DOTALL | re.IGNORECASE,
    )
    if details_match:
        details_inner = details_match.group(1)
        for li in re.finditer(r"<li[^>]*>(.*?)</li>", details_inner, re.DOTALL | re.IGNORECASE):
            msg = re.sub(r"<[^>]+>", "", li.group(1)).strip()
            if msg:
                messages.append(msg)
    # Fallback: any td that looks like a list of messages (multiple <li> or long text)
    if not messages:
        # Try <td> with nested <ul>/<ol> or several <br>-separated lines
        long_td = re.search(
            r"<td[^>]*>(.*?)</td>",
            row_html,
            re.DOTALL | re.IGNORECASE,
        )
        if long_td:
            inner = long_td.group(1)
            for li in re.finditer(r"<li[^>]*>(.*?)</li>", inner, re.DOTALL | re.IGNORECASE):
                msg = re.sub(r"<[^>]+>", "", li.group(1)).strip()
                if msg and len(msg) > 2:
                    messages.append(msg)
            if not messages and len(inner) > 20:
                plain = re.sub(r"<[^>]+>", " ", inner).strip()
                plain = re.sub(r"\s+", " ", plain)
                if plain and plain != claim_id:
                    messages.append(plain[:500])

    return {
        "claim_id": claim_id,
        "outcome": outcome.upper(),
        "error_messages": messages if messages else ["No details"],
        "row_index": row_index,
    }


def parse_claimit_report_html(html_content: str) -> Dict[str, Any]:
    """
    Parse ClaimIT import report HTML.
    Returns:
      overview: { report_date, passed, warning, failed, total }
      errors: [ { claim_id, outcome, error_messages, row_index }, ... ]
    """
    errors: List[Dict[str, Any]] = []
    overview = _extract_overview(html_content)

    # Strategy 1: table id="outcome-rows" — use depth counting so nested <table> don't truncate
    tbody = _find_table_content(html_content, "outcome-rows")
    if tbody:
        # Find each <tr class='ERROR' or class='WARNING'> and its matching </tr> (nested tr exist)
        row_start_pat = re.compile(
            r"<tr[^>]*class=['\"](ERROR|WARNING)['\"][^>]*>",
            re.IGNORECASE,
        )
        row_index = 0
        pos = 0
        while True:
            m = row_start_pat.search(tbody, pos)
            if not m:
                break
            row_index += 1
            end = _find_tr_end(tbody, m.end())
            if end < 0:
                pos = m.end()
                continue
            row_inner = tbody[m.end() : end]
            row = _extract_claim_row(row_inner, m.group(1), row_index)
            if row:
                errors.append(row)
            pos = end + 5  # past </tr>

    # Strategy 2: if no table or no rows, scan all <tr> for claim id + ERROR/WARNING/Failed
    if not errors:
        row_candidates = re.finditer(
            r"<tr[^>]*>(.*?)</tr>",
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        outcome_in_row = re.compile(
            r"(ERROR|WARNING|Failed|Failure|Error\b)",
            re.IGNORECASE,
        )
        row_index = 0
        for m in row_candidates:
            row_html = m.group(0)
            row_inner = m.group(1)
            if not _extract_claim_id_from_row(row_inner):
                continue
            if not outcome_in_row.search(row_html):
                continue
            row_index += 1
            outcome = "ERROR"
            if re.search(r"WARNING", row_html, re.IGNORECASE):
                outcome = "WARNING"
            elif re.search(r"Failed|Failure", row_html, re.IGNORECASE):
                outcome = "ERROR"
            row = _extract_claim_row(row_inner, outcome, row_index)
            if row and not any(e["claim_id"] == row["claim_id"] for e in errors):
                errors.append(row)

    return {"overview": overview, "errors": errors}
