"""
Data contracts and schema definitions for the Colony of Minds framework.
Ensures standardized communication format across all suboperators.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class SuboperatorResponse:
    """
    Standard data contract returned by all suboperators.
    Enforces clean structure, avoiding raw natural language internally.
    """
    operator: str
    success: bool
    confidence: float
    facts: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the response structure to a raw dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuboperatorResponse":
        """Reconstruct the dataclass from a dictionary representation."""
        return cls(
            operator=data.get("operator", "unknown"),
            success=bool(data.get("success", False)),
            confidence=float(data.get("confidence", 0.0)),
            facts=list(data.get("facts", [])),
            warnings=list(data.get("warnings", [])),
            errors=list(data.get("errors", [])),
            evidence=list(data.get("evidence", []))
        )

    @classmethod
    def create_error(cls, operator: str, error_message: str) -> "SuboperatorResponse":
        """Helper to quickly construct a standard error response."""
        return cls(
            operator=operator,
            success=False,
            confidence=0.0,
            errors=[error_message]
        )


@dataclass
class RouterResponse:
    """
    Standard data contract returned by the Router.
    Specifies which suboperators to activate, routing reason, and confidence.
    """
    selected_operators: List[str]
    reason: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert the routing structure to a raw dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RouterResponse":
        """Reconstruct the dataclass from a dictionary representation."""
        return cls(
            selected_operators=list(data.get("selected_operators", [])),
            reason=str(data.get("reason", "")),
            confidence=float(data.get("confidence", 0.0))
        )


@dataclass
class VerificationResult:
    """
    Standard data contract returned by the Verifier.
    Contains clean verified facts, rejected facts, warnings, and missing details.
    """
    verified: bool
    facts: List[Dict[str, Any]] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the verification result structure to a raw dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        """Reconstruct the dataclass from a dictionary representation."""
        return cls(
            verified=bool(data.get("verified", False)),
            facts=list(data.get("facts", [])),
            rejected=list(data.get("rejected", [])),
            warnings=list(data.get("warnings", [])),
            missing=list(data.get("missing", []))
        )

