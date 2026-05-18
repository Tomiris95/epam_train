"""
Agent 2: Recipe Agent (MCP Client)
====================================
Connects to the persistent Recipe MCP Server via HTTP/SSE and calls:
  - search_local_recipes  (FAISS + SQL, local DB)
  - search_online_recipes (Spoonacular fallback, saves to DB)

Falls back to a direct SQL query if the MCP server is unreachable.
"""
import asyncio
import json
import logging
import os
from typing import List, Dict, Optional
from sqlalchemy import func, or_

from sqlalchemy.orm import Session
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

from backend.models import Recipe, RecipeIngredient

logger = logging.getLogger(__name__)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/sse")

_STOPWORDS = {
    # English
    "with", "some", "something", "that", "have", "has", "want", "like",
    "and", "for", "the", "please", "can", "you", "make", "give", "more",
    "less", "instead", "another", "different", "lighter", "heavier",
    # Russian
    "что", "или", "для", "без", "нет", "хочу", "можно", "дай", "другой",
}


class RecipeAgent:
    """
    MCP client that delegates recipe search to the persistent Recipe MCP Server.
    Falls back to direct SQL if the MCP server is unreachable.
    """

    def run(
        self,
        db: Session,
        preference_result: Dict,
        meal_type: str,
        top_k: int = 15,
        exclude_recipe_ids: Optional[List[int]] = None,
        query_hint: str = "",
    ) -> List[Recipe]:
        forbidden   = preference_result.get("forbidden_tags", [])
        allowed     = preference_result.get("allowed_tags", [])
        exclude_ids = set(exclude_recipe_ids or [])
        query       = " ".join(filter(None, [meal_type, query_hint] + list(allowed)))
        # stol5 is a behavioral tag (controls Spoonacular routing), not a content tag.
        # filter_tags drives recipe content matching on all non-MCP paths.
        _BEHAVIORAL = {"stol5"}
        filter_tags = set(allowed) - _BEHAVIORAL

        # ── Step 0: ingredient keyword search (runs first when preference given) ─
        # Catches cases like "eggs", "chicken", "salmon" that FAISS misses due to
        # cross-language gap. Filters out stopwords so "with" doesn't match everything.
        if query_hint:
            keywords = [
                w.lower() for w in query_hint.split()
                if len(w) >= 3 and w.lower() not in _STOPWORDS
            ]
            if keywords:
                # Search both recipe names AND ingredient names so that
                # "smoothie" matches recipe name "Tropical Banana Green Smoothie"
                # even though "smoothie" is not an ingredient.
                name_conditions = [Recipe.name.ilike(f"%{kw}%") for kw in keywords]
                ing_conditions  = [RecipeIngredient.name.ilike(f"%{kw}%") for kw in keywords]
                ing_hits = (
                    db.query(Recipe)
                    .outerjoin(RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id)
                    .filter(
                        Recipe.meal_type == meal_type,
                        ~Recipe.id.in_(exclude_ids),
                        or_(*name_conditions, *ing_conditions),
                    )
                    .distinct()
                    .order_by(func.random())
                    .limit(20)
                    .all()
                )
                if forbidden:
                    ing_hits = [r for r in ing_hits if not any(t.tag in forbidden for t in r.tags)]
                if filter_tags:
                    ing_hits = [r for r in ing_hits if filter_tags.issubset({t.tag for t in r.tags})]
                if ing_hits:
                    logger.info("Ingredient search found %d results for keywords %s.", len(ing_hits), keywords)
                    return ing_hits[:10]
                logger.info("Ingredient search: no results for %s — falling through to FAISS.", keywords)

        # ── Step 1: FAISS + MCP ──────────────────────────────────────────────────
        try:
            recipe_ids = asyncio.run(self._search_via_mcp(
                query=query,
                meal_type=meal_type,
                forbidden_tags=list(forbidden),
                allowed_tags=list(allowed),
                top_k=top_k,
            ))
        except Exception as e:
            logger.warning("MCP call failed (%s), using SQL fallback.", e)
            recipe_ids = []

        if recipe_ids:
            candidates = db.query(Recipe).filter(Recipe.id.in_(recipe_ids)).all()
            filtered = [r for r in candidates if r.id not in exclude_ids]
            if filter_tags:
                filtered = [r for r in filtered if filter_tags.issubset({t.tag for t in r.tags})]
            if filtered:
                return filtered
            # All MCP candidates excluded — fall through to SQL fallback
            logger.info("All MCP candidates excluded — falling back to SQL for %s.", meal_type)

        logger.warning("No usable MCP results — local SQL fallback for %s.", meal_type)
        sql_q = db.query(Recipe).filter(
            Recipe.meal_type == meal_type,
            ~Recipe.id.in_(exclude_ids),
        )
        if "stol5" in allowed:
            sql_q = sql_q.filter(Recipe.source == "local")
        candidates = sql_q.order_by(func.random()).limit(50).all()
        if forbidden:
            candidates = [r for r in candidates if not any(t.tag in forbidden for t in r.tags)]
        if filter_tags:
            candidates = [r for r in candidates if filter_tags.issubset({t.tag for t in r.tags})]
        return candidates[:10]

    async def _search_via_mcp(
        self,
        query: str,
        meal_type: str,
        forbidden_tags: List[str],
        allowed_tags: List[str],
        top_k: int,
    ) -> List[int]:
        async with sse_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # ── Step 1: local FAISS + SQL search ──────────────────────────
                local_result = await session.call_tool(
                    "search_local_recipes",
                    {
                        "query":               query,
                        "meal_type":           meal_type,
                        "forbidden_tags_json": json.dumps(forbidden_tags),
                        "allowed_tags_json":   json.dumps(allowed_tags),
                        "top_k":               top_k,
                    },
                )
                local_data = json.loads(local_result.content[0].text)
                recipe_ids = local_data.get("recipe_ids", [])
                logger.info("Local search → %d results", len(recipe_ids))

                # ── Step 2: online Spoonacular fallback if local is empty ──────
                if not recipe_ids:
                    if "stol5" in allowed_tags:
                        logger.info("stol5 requested — skipping online fallback.")
                        return []
                    logger.info("Local empty — searching Spoonacular online...")
                    online_result = await session.call_tool(
                        "search_online_recipes",
                        {
                            "meal_type":         meal_type,
                            "allowed_tags_json": json.dumps(allowed_tags),
                            "min_health_score":  0,
                        },
                    )
                    online_data = json.loads(online_result.content[0].text)
                    recipe_ids  = online_data.get("recipe_ids", [])
                    logger.info("Online → %d new recipes saved", online_data.get('saved', 0))

                return recipe_ids

    def get_recipe_by_id(self, db: Session, recipe_id: int) -> Optional[Recipe]:
        return db.query(Recipe).filter(Recipe.id == recipe_id).first()

    def get_alternatives(
        self,
        db: Session,
        preference_result: Dict,
        meal_type: str,
        exclude_recipe_id: int,
        limit: int = 5,
        query_hint: str = "",
        disliked_ids: Optional[List[int]] = None,
    ) -> List[Recipe]:
        all_excluded = [exclude_recipe_id] + list(disliked_ids or [])
        candidates = self.run(
            db=db,
            preference_result=preference_result,
            meal_type=meal_type,
            top_k=20,
            exclude_recipe_ids=all_excluded,
            query_hint=query_hint,
        )
        return candidates[:limit]
