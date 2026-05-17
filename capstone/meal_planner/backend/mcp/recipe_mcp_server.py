"""
MCP Server — Recipe Search
==========================
Exposes two tools to MCP clients (RecipeAgent):

  search_local_recipes  — FAISS vector search + SQL tag filtering
  search_online_recipes — Spoonacular API fallback; saves new recipes to DB

Run standalone:
    python backend/mcp/recipe_mcp_server.py
"""

import json
import logging
import os
import random
import sys

logger = logging.getLogger(__name__)

# Ensure project root is on the path when running as a subprocess
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from mcp.server.fastmcp import FastMCP

MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
mcp = FastMCP("Recipe Search", port=MCP_PORT, host="127.0.0.1")
from backend.database import SessionLocal
from backend import models
from backend.rag import vector_store


# ─── Tool 1: Local FAISS + SQL search ────────────────────────────────────────

@mcp.tool()
def search_local_recipes(
    query: str,
    meal_type: str,
    forbidden_tags_json: str,
    allowed_tags_json: str = '[]',
    top_k: int = 15,
) -> str:
    """
    Search the local recipe database using FAISS semantic search,
    then filter results by meal_type and forbidden dietary tags.

    Args:
        query: semantic search string (e.g. "vegan high_protein dinner")
        meal_type: breakfast | lunch | dinner | dessert
        forbidden_tags_json: JSON array of tag strings to exclude
        top_k: number of candidates to retrieve from FAISS

    Returns:
        JSON object: {"recipe_ids": [...], "source": "local"}
    """
    forbidden_tags = set(json.loads(forbidden_tags_json))
    allowed_tags = set(json.loads(allowed_tags_json))
    # Behavioral tags control search strategy, not recipe tag matching
    BEHAVIORAL_TAGS = {"stol5"}
    filter_tags = allowed_tags - BEHAVIORAL_TAGS
    db = SessionLocal()
    try:
        if not vector_store.is_ready():
            recipes = db.query(models.Recipe).all()
            vector_store.load_or_build_index(recipes)

        candidate_ids = vector_store.search(query, top_k=top_k)

        if not candidate_ids:
            candidate_ids = [r.id for r in db.query(models.Recipe).all()]

        stol5_only = "stol5" in allowed_tags

        candidate_q = db.query(models.Recipe).filter(models.Recipe.id.in_(candidate_ids))
        if stol5_only:
            candidate_q = candidate_q.filter(models.Recipe.source == "local")
        candidates = candidate_q.all()

        results = []
        for recipe in candidates:
            recipe_tags = {t.tag for t in recipe.tags}
            if recipe_tags & forbidden_tags:
                continue
            if filter_tags and not filter_tags.issubset(recipe_tags):
                continue
            if recipe.meal_type != meal_type and meal_type not in recipe_tags:
                continue
            results.append(recipe.id)

        # FAISS top-k may not contain any recipes of the requested meal_type.
        # Fall back to querying all recipes of that meal_type directly.
        if not results:
            logger.info(
                "FAISS top-%d had no '%s' recipes — querying all local %s recipes.",
                top_k, meal_type, meal_type,
            )
            fallback_q = db.query(models.Recipe).filter(models.Recipe.meal_type == meal_type)
            if stol5_only:
                fallback_q = fallback_q.filter(models.Recipe.source == "local")
            fallback = fallback_q.all()
            random.shuffle(fallback)
            for recipe in fallback:
                recipe_tags = {t.tag for t in recipe.tags}
                if recipe_tags & forbidden_tags:
                    continue
                if filter_tags and not filter_tags.issubset(recipe_tags):
                    continue
                results.append(recipe.id)

        hit_rate = len(results) / len(candidates) if candidates else 0.0
        logger.info(
            "RAG search_local_recipes meal_type=%s | candidates=%d → passed=%d | hit_rate=%.0f%%",
            meal_type, len(candidates), len(results), hit_rate * 100,
        )
        # Shuffle so callers get variety across repeated calls with the same query
        random.shuffle(results)
        return json.dumps({"recipe_ids": results, "source": "local"})

    finally:
        db.close()


# ─── Tool 2: Online Spoonacular fallback ──────────────────────────────────────

@mcp.tool()
def search_online_recipes(
    meal_type: str,
    allowed_tags_json: str,
    min_health_score: int = 0,
) -> str:
    """
    Search Spoonacular API for recipes when the local DB has no matches.
    Newly found recipes are saved to the local DB for future use.

    Args:
        meal_type: breakfast | lunch | dinner | dessert
        allowed_tags_json: JSON array of preferred tag strings (used to infer diet filter)
        min_health_score: Spoonacular health score threshold 0-100

    Returns:
        JSON object: {"recipe_ids": [...], "source": "online", "saved": N}
    """
    import requests

    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key:
        logger.warning("search_online_recipes: No SPOONACULAR_API_KEY set.")
        return json.dumps({"recipe_ids": [], "source": "online", "saved": 0})

    allowed_tags = json.loads(allowed_tags_json)

    spoon_type_map = {
        "breakfast": "breakfast",
        "lunch":     "salad",
        "dinner":    "main course",
        "dessert":   "dessert",
    }
    spoon_type = spoon_type_map.get(meal_type, "main course")

    params = {
        "apiKey":               api_key,
        "type":                 spoon_type,
        "number":               5,
        "addRecipeInformation": True,
        "addRecipeNutrition":   True,
        "fillIngredients":      True,
        "instructionsRequired": True,
        "sort":                 "healthiness",
        "sortDirection":        "desc",
    }
    if min_health_score > 0:
        params["minHealthScore"] = min_health_score
    if "vegan" in allowed_tags:
        params["diet"] = "vegan"
    elif "vegetarian" in allowed_tags:
        params["diet"] = "vegetarian"

    try:
        r = requests.get(
            "https://api.spoonacular.com/recipes/complexSearch",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        recipes_data = r.json().get("results", [])
    except Exception as e:
        logger.error("search_online_recipes Spoonacular error: %s", e)
        return json.dumps({"recipe_ids": [], "source": "online", "saved": 0, "error": str(e)})

    db = SessionLocal()
    existing_names = {rec.name.lower() for rec in db.query(models.Recipe).all()}
    new_ids = []

    try:
        # Deferred import: spoonacular_seed imports backend.database at module level,
        # which would cause a circular dependency if imported at the top of this file.
        from spoonacular_seed import _save_recipe

        for recipe_data in recipes_data:
            name = recipe_data.get("title", "")
            if not name or name.lower() in existing_names:
                continue
            try:
                recipe_obj = _save_recipe(db, recipe_data, meal_type)
                if recipe_obj:
                    new_ids.append(recipe_obj.id)
                    existing_names.add(name.lower())
                    logger.info("search_online_recipes saved: %s", name)
            except Exception as e:
                logger.error("search_online_recipes failed to save '%s': %s", name, e)

        logger.info("search_online_recipes saved %d new recipes for %s", len(new_ids), meal_type)
        return json.dumps({"recipe_ids": new_ids, "source": "online", "saved": len(new_ids)})

    finally:
        db.close()


if __name__ == "__main__":
    mcp.run(transport="sse")
