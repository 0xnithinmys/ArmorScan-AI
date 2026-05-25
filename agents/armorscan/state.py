from typing import TypedDict, List, Optional, Literal, Any


class FindingDraft(TypedDict):
    id: str
    title: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    cwe_id: Optional[str]
    url: str
    parameter: Optional[str]
    payload: Optional[str]
    evidence: Optional[str]
    confidence: float  # 0.0 - 1.0


class ScanState(TypedDict):
    """
    Shared state passed between all LangGraph agent nodes.
    Each agent reads from and writes to this dict.
    """
    # Scan metadata
    scan_id: str
    target_url: str
    scan_type: Literal["url", "github", "api"]
    status: Literal["idle", "planning", "executing", "observing", "reflecting", "completed", "failed"]

    # Recon outputs
    discovered_routes: List[str]
    discovered_forms: List[dict]
    discovered_inputs: List[dict]
    technology_stack: List[str]
    state_graph: Optional[dict]

    # Planning outputs
    intent_plan: Optional[dict]
    armoriq_token: Optional[str]

    # Exploitation outputs
    findings_drafts: List[FindingDraft]

    # Final outputs
    findings: List[dict]
    report_json: Optional[dict]

    # Agent memory / trace
    agent_trace: List[dict]
    error: Optional[str]
