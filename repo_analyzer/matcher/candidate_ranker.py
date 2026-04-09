from typing import List, Dict
from ..models.entities import FrontendUrl, GatewayRoute


class CandidateRanker:
    def __init__(self):
        pass

    def rank_candidates(self, candidates: List, context: Dict = None) -> List:
        if not candidates:
            return []

        scored = []
        for candidate in candidates:
            score = self._calculate_score(candidate, context)
            scored.append((candidate, score))

        scored.sort(key=lambda x: -x[1])

        return [c for c, s in scored]

    def _calculate_score(self, candidate, context: Dict) -> float:
        if hasattr(candidate, "confidence"):
            base_score = candidate.confidence
        else:
            base_score = 0.5

        adjustments = 0.0

        if context:
            if context.get("method_match"):
                adjustments += 0.1
            if context.get("path_depth_match"):
                adjustments += 0.1

        return min(1.0, base_score + adjustments)

    def filter_low_confidence(self, results: List, threshold: float = 0.4) -> List:
        return [r for r in results if r.confidence >= threshold]

    def get_best_match(self, results: List) -> object:
        if not results:
            return None

        return max(results, key=lambda x: x.confidence)
