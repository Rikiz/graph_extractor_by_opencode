from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class MatchResult:
    match_type: str
    confidence: float
    match_details: Optional[str] = None


@dataclass
class Relation:
    relation_type: str
    match_type: str
    confidence: float
    match_details: Optional[str] = None

    def to_neo4j_dict(self) -> Dict[str, Any]:
        return {
            "match_type": self.match_type,
            "confidence": self.confidence,
            "match_details": self.match_details,
        }
