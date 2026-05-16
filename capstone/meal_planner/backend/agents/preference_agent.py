"""
Agent 1: Preference Agent
Input:  list of FamilyMember objects
Output: dict with combined allowed_tags and forbidden_tags
"""
import logging
from typing import List, Dict, Set
from backend.models import FamilyMember

logger = logging.getLogger(__name__)


class PreferenceAgent:
    """
    Aggregates dietary preferences across all family members.
    A tag is forbidden for the whole family if ANY member forbids it.
    A tag is allowed only if ALL members allow it.
    """

    def run(self, members: List[FamilyMember]) -> Dict:
        allowed_tags: Set[str] = set()
        forbidden_tags: Set[str] = set()

        for member in members:
            for dt in member.diet_tags:
                if dt.is_forbidden:
                    forbidden_tags.add(dt.tag)
                else:
                    allowed_tags.add(dt.tag)

        # Tags cannot be both allowed and forbidden — forbidden wins
        allowed_tags -= forbidden_tags

        result = {
            "allowed_tags": sorted(list(allowed_tags)),
            "forbidden_tags": sorted(list(forbidden_tags)),
            "member_count": len(members),
            "members_summary": [
                {
                    "name": m.name,
                    "calorie_target": m.calorie_target,
                    "tags": [dt.tag for dt in m.diet_tags],
                }
                for m in members
            ],
        }

        logger.info("Forbidden: %s | Allowed: %s", result['forbidden_tags'], result['allowed_tags'])
        return result
