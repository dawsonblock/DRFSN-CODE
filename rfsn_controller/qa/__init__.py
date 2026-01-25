"""QA package for claim-based adversarial verification."""

from .qa_types import (
    Claim,
    ClaimType,
    ClaimVerdict,
    DeltaMapEvidence,
    Evidence,
    EvidenceType,
    PolicyCheckEvidence,
    QAAttempt,
    StaticCheckEvidence,
    TestResultEvidence,
    Verdict,
)
from .claim_extractor import ClaimExtractor, PatchContext, create_claim_extractor
from .qa_critic import QACritic, create_qa_critic
from .evidence_collector import EvidenceCollector, create_evidence_collector
from .qa_gate import QAGate, GateDecision, create_qa_gate
from .qa_persistence import QAPersistence, create_qa_persistence
from .qa_orchestrator import QAOrchestrator, QAConfig, QAResult, create_qa_orchestrator
from .static_checker import StaticChecker, StaticCheckResult, create_static_checker
from .coverage_analyzer import CoverageAnalyzer, CoverageReport, create_coverage_analyzer

__all__ = [
    # Types
    "Claim",
    "ClaimType",
    "ClaimVerdict",
    "DeltaMapEvidence",
    "Evidence",
    "EvidenceType",
    "PolicyCheckEvidence",
    "QAAttempt",
    "StaticCheckEvidence",
    "TestResultEvidence",
    "Verdict",
    # Extractor
    "ClaimExtractor",
    "PatchContext",
    "create_claim_extractor",
    # Critic
    "QACritic",
    "create_qa_critic",
    # Evidence
    "EvidenceCollector",
    "create_evidence_collector",
    # Gate
    "QAGate",
    "GateDecision",
    "create_qa_gate",
    # Persistence
    "QAPersistence",
    "create_qa_persistence",
    # Orchestrator
    "QAOrchestrator",
    "QAConfig",
    "QAResult",
    "create_qa_orchestrator",
    # Static Checker
    "StaticChecker",
    "StaticCheckResult",
    "create_static_checker",
    # Coverage Analyzer
    "CoverageAnalyzer",
    "CoverageReport",
    "create_coverage_analyzer",
]
