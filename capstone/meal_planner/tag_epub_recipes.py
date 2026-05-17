"""
tag_epub_recipes.py
===================
Enriches local (stol5 EPUB) recipes with dietary content tags
based on ingredient analysis. Run once after seeding the DB.

Tags added:
  vegetarian  — no meat, no fish/seafood
  no_red_meat — no beef, pork, lamb, or veal (chicken/fish/turkey OK)
  halal       — no pork, no alcohol (all stol5 recipes qualify)
  low_spice   — no chili or cayenne (all stol5 recipes qualify)
  soft_food   — recipe name indicates soft texture (soups, porridges, purees, etc.)
  toddler     — soft_food + low_spice + no whole-nut or choking-hazard ingredients

Usage:
    python tag_epub_recipes.py
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import SessionLocal
from backend import models

# ── Keyword lists (lowercase Russian substrings) ──────────────────────────────

# Any meat — disqualifies 'vegetarian'
_MEAT = [
    'говяд', 'говяж',   # beef (говядина, говяжий)
    'куриц', 'курин',   # chicken (курица, куриная/ое/ый)
    'индейк',           # turkey (индейка, фарш индейки, филе индейки)
    'кролик',           # rabbit
    'мясн',             # generic meat (фарш мясной, мясной бульон)
    'свинин',           # pork
    'баранин',          # lamb
    'телятин',          # veal
]

# Fish / seafood — disqualifies 'vegetarian'
_FISH = [
    'рыб',      # fish (рыба, рыбный, филе рыбы, нежирной рыбы, рыбное)
    'горбуш',   # pink salmon (горбуша)
    'минтай',   # pollock
    'судак',    # pike-perch
    'треск',    # cod (треска, трески, филе трески)
    'хек',      # hake
    'семг',     # salmon (семга, стейк семги)
    'кальмар',  # squid
    'креветк',  # shrimp (креветки)
    'форел',    # trout (форель)
]

# Red meat only — disqualifies 'no_red_meat'
_RED_MEAT = ['говяд', 'говяж', 'свинин', 'баранин', 'телятин']

# Hot spices — disqualifies 'low_spice'
_SPICY = ['чили', 'кайенн', 'жгучий', 'острый перец']

# Recipe name substrings that indicate soft texture
_SOFT_NAME = [
    'суп', 'пюре', 'каша', 'кисель', 'компот', 'омлет', 'мусс',
    'суфле', 'смузи', 'пудинг', 'соус', 'паштет', 'бульон',
    'коктейль', 'пюрированн',
]

# Ingredients that are choking hazards for toddlers (whole nuts, hard fruits)
_TODDLER_UNSAFE_INGS = ['миндаль', 'черешня']


def _has_any(ingredients: list, keywords: list) -> bool:
    return any(kw in ing for ing in ingredients for kw in keywords)


def _add_tag(db, recipe_id: int, tag: str, existing: set) -> bool:
    if tag not in existing:
        db.add(models.RecipeTag(recipe_id=recipe_id, tag=tag))
        return True
    return False


def run():
    db = SessionLocal()
    try:
        local_recipes = (
            db.query(models.Recipe)
            .filter(models.Recipe.source == "local")
            .all()
        )
        print(f"Processing {len(local_recipes)} local (EPUB) recipes...\n")

        stats: dict[str, int] = {}

        for recipe in local_recipes:
            ings = [i.name.lower() for i in recipe.ingredients]
            existing = {t.tag for t in recipe.tags}

            has_meat     = _has_any(ings, _MEAT)
            has_fish     = _has_any(ings, _FISH)
            has_red_meat = _has_any(ings, _RED_MEAT)
            has_spicy    = _has_any(ings, _SPICY)
            has_toddler_unsafe = _has_any(ings, _TODDLER_UNSAFE_INGS)
            name_lower   = recipe.name.lower()
            is_soft      = any(kw in name_lower for kw in _SOFT_NAME)

            added = []

            # vegetarian: no meat and no fish/seafood
            if not has_meat and not has_fish:
                if _add_tag(db, recipe.id, "vegetarian", existing):
                    added.append("vegetarian")

            # no_red_meat: no beef/pork/lamb/veal (chicken and fish are fine)
            if not has_red_meat:
                if _add_tag(db, recipe.id, "no_red_meat", existing):
                    added.append("no_red_meat")

            # halal: stol5 medical diet has no pork or alcohol — all qualify
            if _add_tag(db, recipe.id, "halal", existing):
                added.append("halal")

            # low_spice: stol5 avoids spicy food — all qualify unless chili found
            if not has_spicy:
                if _add_tag(db, recipe.id, "low_spice", existing):
                    added.append("low_spice")

            # soft_food: recipe name indicates soft texture
            if is_soft:
                if _add_tag(db, recipe.id, "soft_food", existing):
                    added.append("soft_food")

            # toddler: soft + low_spice + no choking hazards
            is_low_spice = not has_spicy
            if is_soft and is_low_spice and not has_toddler_unsafe:
                if _add_tag(db, recipe.id, "toddler", existing):
                    added.append("toddler")

            if added:
                for tag in added:
                    stats[tag] = stats.get(tag, 0) + 1
                print(f"  [{recipe.id}] {recipe.name[:50]} → {', '.join(added)}")

        db.commit()

        print("\n── Summary ──────────────────────────────────")
        for tag, count in sorted(stats.items()):
            print(f"  {tag}: +{count} recipes tagged")
        print(f"\nDone. Run rag_eval.py to see the updated F1 scores.")

    finally:
        db.close()


if __name__ == "__main__":
    run()
