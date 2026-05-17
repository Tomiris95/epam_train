"""
RAG Precision / Recall Evaluation
===================================
Evaluates the retrieval quality of the Recipe Agent (FAISS + SQL fallback)
against a SQL-generated ground truth.

Ground truth: recipes whose name or ingredients match the query keywords —
  these are the recipes the system *should* return for a given query.

Usage:
    python rag_eval.py                    # runs all test cases, saves rag_eval_results.json
    python rag_eval.py --meal-type dinner # filter by meal type
    python rag_eval.py --top-k 15        # change FAISS top-k (default 10)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import or_

from backend.database import SessionLocal
from backend.models import Recipe, RecipeIngredient
from backend.agents.recipe_agent import RecipeAgent

# ─────────────────────────────────────────────────────────────────────────────
# Test queries
# Each entry has:
#   query      – the natural-language search string sent to FAISS
#   meal_type  – the meal slot filter
#   keywords   – Russian + English substrings used to build SQL ground truth
#   tags       – simulated user preference tags (empty = no dietary filter)
# ─────────────────────────────────────────────────────────────────────────────
TEST_CASES = [
    # ── Breakfast ─────────────────────────────────────────────────────────────
    {
        "query":     "breakfast with eggs",
        "meal_type": "breakfast",
        "keywords":  ["яйц", "белок яич", "egg"],
        "tags":      [],
        "note":      "Should find omelettes, egg dishes",
    },
    {
        "query":     "porridge oatmeal breakfast",
        "meal_type": "breakfast",
        "keywords":  ["каш", "oat", "porridge", "oatmeal"],
        "tags":      [],
        "note":      "'oatmeal' matches Spoonacular recipe names; 'каш' matches Russian EPUB names",
    },
    {
        "query":     "творог сырники обед",
        "meal_type": "lunch",
        "keywords":  ["творог", "сырник", "cottage cheese", "curd"],
        "tags":      [],
        "note":      "Russian query — 'сырник' matches recipe name directly in FAISS",
    },
    {
        "query":     "smoothie banana breakfast",
        "meal_type": "breakfast",
        "keywords":  ["smoothie", "смузи"],
        "tags":      [],
        "note":      "'smoothie' now matches Spoonacular recipe names (not just ingredients)",
    },
    {
        "query":     "halal breakfast",
        "meal_type": "breakfast",
        "keywords":  ["halal"],
        "tags":      ["halal"],
        "note":      "Halal-tagged breakfast recipes from Spoonacular",
    },

    # ── Lunch ─────────────────────────────────────────────────────────────────
    {
        "query":     "chicken soup lunch",
        "meal_type": "lunch",
        "keywords":  ["курица", "chicken", "суп", "soup"],
        "tags":      [],
        "note":      "Chicken soups",
    },
    {
        "query":     "vegetable salad lunch",
        "meal_type": "lunch",
        "keywords":  ["салат", "salad", "овощ", "vegetable"],
        "tags":      [],
        "note":      "Salads and vegetable dishes",
    },
    {
        "query":     "lentil soup",
        "meal_type": "lunch",
        "keywords":  ["чечевица", "lentil"],
        "tags":      [],
        "note":      "Lentil-based dishes",
    },
    {
        "query":     "fish lunch",
        "meal_type": "lunch",
        "keywords":  ["рыб", "fish", "salmon", "лосос", "треск", "семг", "хек", "минтай", "cod"],
        "tags":      [],
        "note":      "Fish dishes for lunch — use Russian roots to catch all grammatical forms",
    },

    # ── Dinner ────────────────────────────────────────────────────────────────
    {
        "query":     "dinner with chicken",
        "meal_type": "dinner",
        "keywords":  ["курица", "chicken", "куриц"],
        "tags":      [],
        "note":      "Chicken-based dinners",
    },
    {
        "query":     "fish dinner",
        "meal_type": "dinner",
        "keywords":  ["рыб", "fish", "salmon", "лосос", "семг", "треск", "cod", "тунец", "tuna", "хек", "минтай"],
        "tags":      [],
        "note":      "Fish-based dinners — use Russian roots to catch all grammatical forms",
    },
    {
        "query":     "beef dinner",
        "meal_type": "dinner",
        "keywords":  ["говядина", "beef", "мясо", "meat"],
        "tags":      [],
        "note":      "Beef/meat dinners",
    },
    {
        "query":     "vegetarian dinner",
        "meal_type": "dinner",
        "keywords":  [],
        "tags":      ["vegetarian"],
        "note":      "Tag-based vegetarian dinner — ground truth and retrieval both use vegetarian tag",
    },
    {
        "query":     "light dinner with vegetables",
        "meal_type": "dinner",
        "keywords":  ["овощ", "vegetable", "брокколи", "broccoli", "морковь", "carrot"],
        "tags":      [],
        "note":      "Light vegetable-based dinners",
    },

]


# ─────────────────────────────────────────────────────────────────────────────
# Ground truth builder
# ─────────────────────────────────────────────────────────────────────────────
def build_ground_truth(db, meal_type: str, keywords: list, tags: list) -> set:
    """
    Returns the set of recipe IDs that are 'correct' for this query.

    A recipe is relevant if:
      - meal_type matches
      - AND (keywords found in recipe name or any ingredient name)
      - OR (tags match recipe tags)
    """
    q = db.query(Recipe).filter(Recipe.meal_type == meal_type)

    filters = []

    # Keyword match on recipe name or ingredient name
    # Materialize IDs to avoid SQLAlchemy 2.0 subquery issues
    if keywords:
        name_filters = [Recipe.name.ilike(f"%{kw}%") for kw in keywords]
        ingredient_recipe_ids = [
            row.recipe_id
            for row in db.query(RecipeIngredient.recipe_id)
            .filter(or_(*[RecipeIngredient.name.ilike(f"%{kw}%") for kw in keywords]))
            .all()
        ]
        if ingredient_recipe_ids:
            filters.append(or_(*name_filters, Recipe.id.in_(ingredient_recipe_ids)))
        else:
            filters.append(or_(*name_filters))

    # Tag match — materialize IDs to avoid SQLAlchemy 2.0 subquery issues
    if tags:
        from backend.models import RecipeTag
        for tag in tags:
            tagged_ids = [
                row.recipe_id
                for row in db.query(RecipeTag.recipe_id).filter(RecipeTag.tag == tag).all()
            ]
            if tagged_ids:
                filters.append(Recipe.id.in_(tagged_ids))

    if filters:
        q = q.filter(or_(*filters))

    return {r.id for r in q.distinct().all()}


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation runner
# ─────────────────────────────────────────────────────────────────────────────
def evaluate(top_k: int = 10, meal_type_filter: str = None) -> list:
    db = SessionLocal()
    agent = RecipeAgent()
    results = []

    cases = TEST_CASES
    if meal_type_filter:
        cases = [c for c in cases if c["meal_type"] == meal_type_filter]

    print(f"\n{'='*70}")
    print(f"  RAG Evaluation — top_k={top_k} | {len(cases)} test cases")
    print(f"{'='*70}")
    print(f"  {'Query':<35} {'MT':<10} P      R      F1     GT  Ret TP")
    print(f"  {'-'*35} {'-'*10} {'-'*6} {'-'*6} {'-'*6} {'-'*3} {'-'*3} {'-'*3}")

    for case in cases:
        ground_truth = build_ground_truth(db, case["meal_type"], case["keywords"], case["tags"])

        preference_result = {
            "forbidden_tags": [],
            "allowed_tags": case["tags"],
        }

        try:
            returned_recipes = agent.run(
                db=db,
                preference_result=preference_result,
                meal_type=case["meal_type"],
                top_k=top_k,
                query_hint=case["query"],
            )
            returned_ids = {r.id for r in returned_recipes}
        except Exception as e:
            print(f"  ERROR on '{case['query']}': {e}")
            returned_ids = set()

        tp = returned_ids & ground_truth
        precision = len(tp) / len(returned_ids) if returned_ids else 0.0
        recall    = len(tp) / len(ground_truth) if ground_truth else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)

        label = case["query"][:35]
        mt    = case["meal_type"][:10]
        print(f"  {label:<35} {mt:<10} {precision:.3f}  {recall:.3f}  {f1:.3f}  "
              f"{len(ground_truth):>3} {len(returned_ids):>3} {len(tp):>3}")

        results.append({
            "query":           case["query"],
            "meal_type":       case["meal_type"],
            "tags":            case["tags"],
            "note":            case.get("note", ""),
            "ground_truth_n":  len(ground_truth),
            "returned_n":      len(returned_ids),
            "true_positives":  len(tp),
            "precision":       round(precision, 4),
            "recall":          round(recall, 4),
            "f1":              round(f1, 4),
            "ground_truth_ids": sorted(ground_truth),
            "returned_ids":     sorted(returned_ids),
            "missed_ids":       sorted(ground_truth - returned_ids),
        })

    db.close()

    # ── Summary ──────────────────────────────────────────────────────────────
    if results:
        avg_p  = sum(r["precision"] for r in results) / len(results)
        avg_r  = sum(r["recall"]    for r in results) / len(results)
        avg_f1 = sum(r["f1"]        for r in results) / len(results)

        print(f"\n  {'AVERAGE':<35} {'':10} {avg_p:.3f}  {avg_r:.3f}  {avg_f1:.3f}")
        print(f"{'='*70}")

        print(f"\n  Best  F1: {max(results, key=lambda x: x['f1'])['query']} "
              f"({max(results, key=lambda x: x['f1'])['f1']:.3f})")
        print(f"  Worst F1: {min(results, key=lambda x: x['f1'])['query']} "
              f"({min(results, key=lambda x: x['f1'])['f1']:.3f})")

        zero_gt = [r for r in results if r["ground_truth_n"] == 0]
        if zero_gt:
            print(f"\n  ⚠️  {len(zero_gt)} query/ies had 0 ground-truth recipes "
                  f"(keywords not found in DB):")
            for r in zero_gt:
                print(f"     • {r['query']}")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Save results
# ─────────────────────────────────────────────────────────────────────────────
def save_results(results: list, path: str = "rag_eval_results.json"):
    payload = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": len(results),
        "averages": {
            "precision": round(sum(r["precision"] for r in results) / len(results), 4) if results else 0,
            "recall":    round(sum(r["recall"]    for r in results) / len(results), 4) if results else 0,
            "f1":        round(sum(r["f1"]        for r in results) / len(results), 4) if results else 0,
        },
        "results": results,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality")
    parser.add_argument("--top-k",     type=int, default=10,  help="FAISS top-k (default 10)")
    parser.add_argument("--meal-type", type=str, default=None,
                        choices=["breakfast", "lunch", "dinner"],
                        help="Filter to one meal type")
    parser.add_argument("--output",    type=str, default="rag_eval_results.json",
                        help="Output JSON file path")
    args = parser.parse_args()

    results = evaluate(top_k=args.top_k, meal_type_filter=args.meal_type)
    if results:
        save_results(results, args.output)
