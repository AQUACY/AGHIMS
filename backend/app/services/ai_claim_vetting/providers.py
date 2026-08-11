"""LLM / analysis provider interfaces for AI claim vetting."""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.services.ai_claim_vetting.rules import run_phase1_rules
from app.services.ai_claim_vetting.schemas import SuggestedAction, VettingFinding

logger = logging.getLogger(__name__)

_ALLOWED_SEVERITIES = frozenset({"critical", "warning", "review_needed"})
_ALLOWED_ACTION_TYPES = frozenset(
    {
        "review_member",
        "review_diagnosis",
        "review_procedure",
        "review_medicine",
        "review_investigation",
        "review_claim",
    }
)

# Deterministic rule topics — LLM should not restate these when already present.
_RULE_TOPIC_HINTS = {
    "specialty_zoom": ("specialty", "zoom", "opdc"),
    "ghana_card_member_no": ("ghana card", "member no", "hin", "nhia"),
}

_SYSTEM_PROMPT = """You are a Ghana NHIA / ClaimIT claim pre-screener for hospital staff.
You NEVER apply changes. You only suggest findings for a human to approve or reject.

Focus on ClaimIT prep issues a human should review, ONLY when clearly evidenced by the payload values:
- Specialty Attended wrong (e.g. value is literally ZOOM instead of OPDC)
- Ghana Card used as memberNo when HIN is required (memberNo looks like a Ghana Card)
- Missing or inconsistent member/HIN fields when those fields are blank or contradictory
- Obvious ICD / GDRG / diagnosis mismatches when both codes are present
- Incomplete claim sections that would fail audit (empty diagnoses, etc.)

Return ONLY valid JSON (no markdown) with this shape:
{"findings":[{"rule_code":"llm_review_<short>","finding":"...","severity":"critical|warning|review_needed","explanation":"...","recommendation":"...","suggested_action":{"type":"review_claim","field":null,"value":null,"details":{}}}]}

Rules:
- Max 5 findings. Prefer fewer high-value items.
- If nothing noteworthy beyond the existing deterministic findings, return {"findings":[]}.
- Do NOT restate or paraphrase issues already listed in existing deterministic findings.
- Do NOT invent problems. Every finding must cite an actual field value from the payload.
- Never claim specialty is ZOOM unless specialtyAttended/specialty is exactly ZOOM.
- Never claim memberNo is a Ghana Card unless that value looks like a Ghana Card.
- Do not invent codes or HINs. If unsure, use severity review_needed and type review_*.
- suggested_action.type must be one of: review_member, review_diagnosis, review_procedure, review_medicine, review_investigation, review_claim.
- Keep explanations short and actionable for Ghana claims staff.
"""


class VettingProvider(ABC):
    name: str = "base"

    @abstractmethod
    def analyze(self, payload: Dict[str, Any]) -> List[VettingFinding]:
        raise NotImplementedError


class RulesOnlyProvider(VettingProvider):
    """Deterministic rules — default Phase-1 provider (no LLM required)."""

    name = "rules"

    def analyze(self, payload: Dict[str, Any]) -> List[VettingFinding]:
        return run_phase1_rules(payload)


class OllamaProvider(VettingProvider):
    """
    Optional Ollama enrichment.
    - llm_only=False: rules first, then LLM additive findings
    - llm_only=True: local-model assist only (dedicated Intelligence card)
    """

    name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        *,
        llm_only: bool = False,
    ):
        self.base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or "llama3.2"
        self.timeout = timeout
        self.llm_only = llm_only
        if llm_only:
            self.name = "ollama_assist"

    def analyze(self, payload: Dict[str, Any]) -> List[VettingFinding]:
        if self.llm_only:
            return self._llm_findings(payload or {}, existing=[])
        findings = run_phase1_rules(payload)
        llm_findings = self._llm_findings(payload or {}, existing=findings)
        if not llm_findings:
            return findings
        return findings + llm_findings

    def _llm_findings(
        self,
        payload: Dict[str, Any],
        *,
        existing: List[VettingFinding],
    ) -> List[VettingFinding]:
        if not self._ping():
            return []

        claim_slice = _compact_claim_payload(payload)
        existing_codes = [f.rule_code for f in existing]
        existing_summaries = [
            {"rule_code": f.rule_code, "finding": f.finding}
            for f in existing
        ]
        user_prompt = (
            "Existing deterministic findings (already covered — do NOT repeat):\n"
            f"{json.dumps(existing_summaries, ensure_ascii=False)}\n\n"
            f"Claim payload:\n{json.dumps(claim_slice, ensure_ascii=False, default=str)}"
        )

        try:
            raw = self._chat(user_prompt)
        except Exception as exc:
            logger.warning("Ollama claim vetting call failed: %s", exc)
            return []

        parsed = _parse_findings_json(raw)
        if parsed is None:
            logger.warning("Ollama returned unparseable findings; ignoring LLM layer")
            return []

        out: List[VettingFinding] = []
        seen = set(existing_codes)
        for item in parsed:
            finding = _normalize_finding(item)
            if finding is None:
                continue
            if finding.rule_code in seen:
                continue
            if _duplicates_existing_topic(finding, existing_codes):
                continue
            if _contradicts_payload(finding, payload):
                continue
            seen.add(finding.rule_code)
            out.append(finding)
            if len(out) >= 5:
                break
        return out

    def _ping(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=min(self.timeout, 3.0)):
                return True
        except Exception:
            return False

    def _chat(self, user_prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 800,
                },
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail or exc.reason}") from exc
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise ValueError("Ollama response missing message.content")
        return content


def _compact_claim_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Keep prompt small — only fields useful for ClaimIT prep review."""
    keys = (
        "claimID",
        "claim_id",
        "memberNo",
        "member_no",
        "hin",
        "HIN",
        "ghanaCard",
        "specialtyAttended",
        "specialty_attended",
        "specialty",
        "principalGDRG",
        "principal_gdrg",
        "typeOfAttendance",
        "dateOfAttendance",
        "outcome",
    )
    out: Dict[str, Any] = {}
    for key in keys:
        if key in payload and payload[key] not in (None, "", []):
            out[key] = payload[key]

    diagnoses = payload.get("diagnoses") or payload.get("diagnosis")
    if isinstance(diagnoses, list):
        out["diagnoses"] = [_compact_line(d, ("icdCode", "icd", "gdrgCode", "gdrg", "GDRG", "isPrincipal", "description", "diagnosis")) for d in diagnoses[:8]]
    elif isinstance(diagnoses, str) and diagnoses.strip():
        out["diagnosis"] = diagnoses.strip()[:200]

    for src, dest, limit in (
        ("procedures", "procedures", 6),
        ("medicines", "medicines", 8),
        ("medications", "medications", 8),
        ("investigations", "investigations", 6),
    ):
        rows = payload.get(src)
        if isinstance(rows, list) and rows:
            out[dest] = [_compact_line(r, None) for r in rows[:limit]]

    return out


def _compact_line(row: Any, prefer_keys: Optional[tuple] = None) -> Any:
    if not isinstance(row, dict):
        return str(row)[:120]
    if prefer_keys:
        slim = {k: row[k] for k in prefer_keys if k in row and row[k] not in (None, "")}
        if slim:
            return slim
    # Generic fallback — first few non-empty scalar fields
    slim = {}
    for k, v in row.items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, (str, int, float, bool)):
            slim[k] = v if not isinstance(v, str) else v[:120]
        if len(slim) >= 6:
            break
    return slim or {k: str(v)[:80] for k, v in list(row.items())[:3]}


def _parse_findings_json(raw: str) -> Optional[List[Dict[str, Any]]]:
    text = (raw or "").strip()
    if not text:
        return None
    # Strip accidental markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to locate first {...} block
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        findings = data.get("findings")
        if isinstance(findings, list):
            return [x for x in findings if isinstance(x, dict)]
        # Single finding object
        if "finding" in data or "rule_code" in data:
            return [data]
    return None


def _normalize_finding(item: Dict[str, Any]) -> Optional[VettingFinding]:
    finding_text = str(item.get("finding") or "").strip()
    if not finding_text:
        return None

    rule_code = str(item.get("rule_code") or "llm_review").strip() or "llm_review"
    rule_code = re.sub(r"[^a-zA-Z0-9_]+", "_", rule_code)[:64]
    if not rule_code.startswith("llm_"):
        rule_code = f"llm_{rule_code}"

    severity = str(item.get("severity") or "review_needed").strip().lower()
    if severity not in _ALLOWED_SEVERITIES:
        severity = "review_needed"

    explanation = str(item.get("explanation") or finding_text).strip()[:2000]
    recommendation = str(item.get("recommendation") or "Human review required.").strip()[:1000]

    action = None
    raw_action = item.get("suggested_action")
    if isinstance(raw_action, dict):
        action_type = str(raw_action.get("type") or "review_claim").strip()
        if action_type not in _ALLOWED_ACTION_TYPES:
            action_type = "review_claim"
        details = raw_action.get("details")
        if not isinstance(details, dict):
            details = {}
        action = SuggestedAction(
            type=action_type,
            field=(str(raw_action["field"]) if raw_action.get("field") not in (None, "") else None),
            value=(str(raw_action["value"]) if raw_action.get("value") not in (None, "") else None),
            details=details,
        )
    else:
        action = SuggestedAction(type="review_claim")

    return VettingFinding(
        rule_code=rule_code,
        finding=finding_text[:500],
        severity=severity,
        explanation=explanation,
        recommendation=recommendation,
        suggested_action=action,
        requires_human_review=True,
    )


def _duplicates_existing_topic(finding: VettingFinding, existing_codes: List[str]) -> bool:
    """Drop LLM rows that restate known deterministic Phase-1 topics."""
    blob = f"{finding.finding} {finding.explanation} {finding.recommendation}".lower()
    for code in existing_codes:
        hints = _RULE_TOPIC_HINTS.get(code)
        if not hints:
            continue
        if any(h in blob for h in hints):
            return True
    return False


def _contradicts_payload(finding: VettingFinding, payload: Dict[str, Any]) -> bool:
    """Reject common small-model hallucinations that ignore actual field values."""
    blob = f"{finding.finding} {finding.explanation} {finding.recommendation}".lower()
    specialty = (
        payload.get("specialtyAttended")
        or payload.get("specialty_attended")
        or payload.get("specialty")
        or ""
    )
    specialty_u = str(specialty).strip().upper()
    member = str(payload.get("memberNo") or payload.get("member_no") or "").strip()

    if "zoom" in blob and specialty_u != "ZOOM":
        return True

    ghana_ish = ("ghana card" in blob) or ("gha-" in blob)
    if ghana_ish:
        try:
            from app.utils.ghims_card import is_ghana_card

            if not is_ghana_card(member):
                return True
        except Exception:
            if not member.upper().startswith("GHA-"):
                return True
    return False


def get_provider(provider_name: str | None = None) -> VettingProvider:
    from app.core.config import settings

    name = (provider_name or getattr(settings, "AI_CLAIM_VETTING_PROVIDER", "rules") or "rules").lower()
    if name in ("ollama", "ollama_assist"):
        return OllamaProvider(
            base_url=getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model=getattr(settings, "OLLAMA_MODEL", "llama3.2"),
            timeout=float(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 60.0) or 60.0),
            llm_only=(name == "ollama_assist"),
        )
    return RulesOnlyProvider()
