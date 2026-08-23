"""
Entity Resolution Algorithm Fix — Phase 26-B.5

CHANGES:
1. REMOVED: Dangerous prefix matching (name[:3])
2. ADDED: Word boundary matching with regex
3. ADDED: Score-based ranking with competition detection
4. ADDED: Anti-Collapse Gate validation
5. ADDED: Unresolved-first design (medium/low confidence → unresolved)

PRINCIPLES:
- False Positive cost >> Unresolved cost
-宁可 unresolved, 不可错绑
- 无法可靠判断时返回 None, 不选择"最接近"的 Entity
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class EntityResolutionResult:
    """Result of entity resolution with score and confidence."""

    def __init__(
        self,
        entity_id: Any | None = None,
        score: float = 0.0,
        confidence: float = 0.0,
        method: str | None = None,
        is_competing: bool = False,
        competing_entities: list[Any] | None = None,
    ):
        self.entity_id = entity_id
        self.score = score
        self.confidence = confidence
        self.method = method
        self.is_competing = is_competing
        self.competing_entities = competing_entities or []

    @property
    def is_unresolved(self) -> bool:
        return self.entity_id is None

    def to_tuple(self) -> tuple[Any | None, str | None]:
        return self.entity_id, self.method


def calculate_match_score(
    entity_name: str,
    content: str,
    use_word_boundary: bool = True
) -> float:
    """Calculate match confidence score.

    Scoring rules:
    - Exact phrase match: 1.0
    - Word boundary match: 0.9
    - Prefix match (length >= 5): 0.5
    - No match: 0.0

    Returns score in [0.0, 1.0]
    """
    entity_lower = entity_name.lower()
    content_lower = content.lower()

    # Rule 1: Exact phrase match (highest confidence)
    if entity_lower in content_lower:
        return 1.0

    # Rule 2: Word boundary match (high confidence)
    if use_word_boundary:
        # Escape special regex characters in entity name
        escaped = re.escape(entity_lower)
        pattern = r'\b' + escaped + r'\b'
        if re.search(pattern, content_lower):
            return 0.9

    # Rule 3: Prefix match with minimum length (medium confidence)
    # MUST require length >= 5 to avoid "win" matching "winner", "within", etc.
    if len(entity_lower) >= 5:
        prefix = entity_lower[:5]
        if prefix in content_lower:
            # Additional check: ensure it's not just a random substring
            # by verifying the prefix is followed by a word boundary or end
            pattern = re.escape(prefix) + r'(\s|[^a-zA-Z]|$)'
            if re.search(pattern, content_lower):
                return 0.5

    # Rule 4: No match
    return 0.0


def detect_competing_entities(
    entity_name: str,
    content: str,
    all_entities: list[Any],
    threshold: float = 0.7
) -> list[Any]:
    """Detect if multiple entities have similar scores.

    Returns list of competing entities with score >= threshold.
    """
    competitors = []
    content_lower = content.lower()

    for entity in all_entities:
        if entity.id == entity_name:
            continue

        score = calculate_match_score(entity.canonical_name, content)
        if score >= threshold:
            competitors.append({
                'id': entity.id,
                'name': entity.canonical_name,
                'score': score
            })

    return competitors


def resolve_entity_strict(
    evidence_content: str,
    workspace_entities: list[Any],
    context_window: list[Any] | None = None,
    min_confidence: float = 0.8
) -> EntityResolutionResult:
    """Strict entity resolution with anti-collapse protection.

    Algorithm:
    1. Calculate match score for each entity
    2. Detect competing entities
    3. Apply confidence threshold
    4. Return unresolved if ambiguous or low confidence
    """
    best_score = 0.0
    best_entity = None
    best_method = None

    for entity in workspace_entities:
        # Calculate score
        score = calculate_match_score(entity.canonical_name, evidence_content)

        # Update best match
        if score > best_score:
            best_score = score
            best_entity = entity
            best_method = _get_match_method(score, entity.canonical_name, evidence_content)

    # Check for competing entities
    competitors = []
    if best_entity and best_score > 0:
        competitors = detect_competing_entities(
            best_entity.id,
            evidence_content,
            workspace_entities,
            threshold=best_score * 0.8  # Within 80% of best score
        )

    # Apply confidence gate
    if best_score < min_confidence:
        logger.debug(
            "Entity resolution: score %.2f < threshold %.2f, marking as unresolved",
            best_score, min_confidence
        )
        return EntityResolutionResult(
            entity_id=None,
            score=best_score,
            confidence=best_score,
            method="unresolved_low_confidence"
        )

    # Check for competition
    if competitors:
        logger.warning(
            "Entity resolution: competing entities detected for '%s': %s",
            evidence_content[:50],
            [c['name'] for c in competitors]
        )
        return EntityResolutionResult(
            entity_id=None,
            score=best_score,
            confidence=best_score,
            method="unresolved_competing",
            is_competing=True,
            competing_entities=[c['name'] for c in competitors]
        )

    # Success: clear match with no competition
    logger.info(
        "Entity resolution: matched '%s' with score %.2f, method '%s'",
        evidence_content[:50],
        best_score,
        best_method
    )
    return EntityResolutionResult(
        entity_id=best_entity.id if best_entity else None,
        score=best_score,
        confidence=best_score,
        method=best_method
    )


def _get_match_method(score: float, entity_name: str, content: str) -> str:
    """Determine the resolution method based on score and content."""
    content_lower = content.lower()
    entity_lower = entity_name.lower()

    if score >= 0.95:
        return "exact_match"
    elif score >= 0.85:
        escaped = re.escape(entity_lower)
        pattern = r'\b' + escaped + r'\b'
        if re.search(pattern, content_lower):
            return "word_boundary_match"
        return "phrase_match"
    elif score >= 0.5:
        return "prefix_match"
    else:
        return "no_match"
