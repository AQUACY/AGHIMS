"""LLM / analysis provider interfaces for AI claim vetting."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.services.ai_claim_vetting.rules import run_phase1_rules
from app.services.ai_claim_vetting.schemas import VettingFinding


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
    Optional Ollama enrichment. Phase 1 still runs rules first;
    Ollama may add narrative findings later. Falls back to rules on failure.
    """

    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 30.0):
        self.base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or "llama3.2"
        self.timeout = timeout

    def analyze(self, payload: Dict[str, Any]) -> List[VettingFinding]:
        # Always include deterministic findings; LLM is additive later.
        findings = run_phase1_rules(payload)
        # Placeholder hook: attempt a health ping; ignore failures.
        try:
            import urllib.request

            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=min(self.timeout, 3.0)):
                pass
        except Exception:
            # Ollama unavailable — rules-only result is still valid.
            return findings
        return findings


def get_provider(provider_name: str | None = None) -> VettingProvider:
    from app.core.config import settings

    name = (provider_name or getattr(settings, "AI_CLAIM_VETTING_PROVIDER", "rules") or "rules").lower()
    if name == "ollama":
        return OllamaProvider(
            base_url=getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model=getattr(settings, "OLLAMA_MODEL", "llama3.2"),
            timeout=float(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 30.0) or 30.0),
        )
    return RulesOnlyProvider()
