"""
Match a stocktaking-sheet name to a GHIMS drug name.

The paper sheet uses short labels ("TAB. PARACETAMOL"). GHIMS uses its own
wording ("Paracetamol Tablet 500mg"). A request is allowed when the name is
the GHIMS name. Reconciliation uses the same comparison.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence


_PUNCT = re.compile(r"[^a-z0-9.]+")
_NUMBER = re.compile(r"^\d+(?:\.\d+)?$")
_LETTER_NUM = re.compile(r"^[a-z]\d+$")

# tablet/capsule are written loosely on the paper sheet ("TAB." covers both).
_SOFT_FORMS = {"tablet", "capsule"}
_FORM_WORDS = {
    "tab": "tablet",
    "tabs": "tablet",
    "tablet": "tablet",
    "tablets": "tablet",
    "cap": "capsule",
    "caps": "capsule",
    "capsule": "capsule",
    "capsules": "capsule",
    "inj": "injection",
    "injection": "injection",
    "syr": "syrup",
    "syrup": "syrup",
    "susp": "suspension",
    "suspension": "suspension",
    "gel": "gel",
    "cream": "cream",
    "drop": "drop",
    "drops": "drop",
    "infusion": "infusion",
    "ointment": "ointment",
}
_DROP = {
    "mg",
    "mcg",
    "ml",
    "g",
    "iu",
    "xl",
    "s",
    "the",
    "and",
    "of",
    "hm",
    "bpc",
    "plus",
    "top",
    "pharmacy",
}


@dataclass
class ParsedName:
    form: Optional[str]
    words: frozenset
    strengths: frozenset


@dataclass
class NameMatch:
    drug_id: Optional[str]
    drug_name: Optional[str]
    ambiguous: bool
    options: list


def parse_name(value: str) -> ParsedName:
    text = (value or "").lower().replace("&", " and ")
    text = text.replace("hydrochlorthiazide", "hctz").replace("hydrochlorothiazide", "hctz")
    text = text.replace("htz", "hctz")
    text = _PUNCT.sub(" ", text)
    form = None
    words = []
    strengths = []
    for raw in text.split():
        token = raw.strip(".")
        if not token or token in _DROP:
            continue
        if token[:1].isdigit():
            token = re.sub(r"(mcg|mg|ml|iu|g)$", "", token)
        if token in _FORM_WORDS:
            mapped = _FORM_WORDS[token]
            if form is None:
                form = mapped
            elif form != mapped and not (form in _SOFT_FORMS and mapped in _SOFT_FORMS):
                form = mapped
            continue
        if _NUMBER.match(token):
            strengths.append(token)
            continue
        if _LETTER_NUM.match(token):
            continue
        words.append(token)
    return ParsedName(form=form, words=frozenset(words), strengths=frozenset(strengths))


def forms_conflict(left: Optional[str], right: Optional[str]) -> bool:
    if not left or not right or left == right:
        return False
    if left in _SOFT_FORMS and right in _SOFT_FORMS:
        return False
    return True


def names_compatible(left: str, right: str) -> bool:
    a = parse_name(left)
    b = parse_name(right)
    if not a.words or not b.words:
        return False
    if forms_conflict(a.form, b.form):
        return False
    if a.strengths and b.strengths and a.strengths != b.strengths:
        return False
    smaller, larger = (a.words, b.words) if len(a.words) <= len(b.words) else (b.words, a.words)
    if smaller <= larger:
        return True
    union = a.words | b.words
    return len(a.words & b.words) / len(union) >= 0.6


def _score(query: ParsedName, candidate: ParsedName) -> float:
    if not query.words or not candidate.words:
        return 0.0
    union = query.words | candidate.words
    return len(query.words & candidate.words) / len(union)


def match_drug(query_name: str, candidates: Sequence[dict]) -> NameMatch:
    """Pick one GHIMS drug for a sheet or requisition name.

    candidates items need drug_id and drug_name.
    """
    parsed = parse_name(query_name)
    accepted = []
    for item in candidates:
        name = item.get("drug_name") or ""
        other = parse_name(name)
        if not names_compatible(query_name, name):
            continue
        accepted.append(((_score(parsed, other), len(other.words)), item))
    if not accepted:
        return NameMatch(drug_id=None, drug_name=None, ambiguous=False, options=[])
    accepted.sort(key=lambda pair: pair[0], reverse=True)
    best_key = accepted[0][0]
    tied = [item for key, item in accepted if abs(key[0] - best_key[0]) < 0.05]
    # Same drug listed twice (two payer groups) is one drug.
    distinct = {}
    for item in tied:
        distinct[item.get("drug_id") or item.get("drug_name")] = item
    options = list(distinct.values())
    if len(options) > 1:
        return NameMatch(drug_id=None, drug_name=None, ambiguous=True, options=options)
    chosen = options[0]
    return NameMatch(
        drug_id=chosen.get("drug_id"),
        drug_name=chosen.get("drug_name"),
        ambiguous=False,
        options=options,
    )


def catalog_names(rows: Iterable) -> list:
    return [{"drug_id": row.drug_id, "drug_name": row.drug_name} for row in rows]
