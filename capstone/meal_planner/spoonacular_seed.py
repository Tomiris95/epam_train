"""
spoonacular_seed.py
====================
Fetch real recipes from the Spoonacular API and populate the meal_planner DB.

Usage:
    python spoonacular_seed.py --api-key YOUR_KEY --count 150

Free tier: ~150 points/day. Each recipe fetch = ~1-1.5 points.
Run over 2 days to get 200-300 recipes safely.
"""

import argparse
import sys
import time
import os
import requests
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import engine, SessionLocal
from backend import models

# ─── Spoonacular API helpers ─────────────────────────────────────────────────

BASE_URL = "https://api.spoonacular.com"


def search_recipes(api_key: str, meal_type: str, offset: int = 0, number: int = 20, min_health_score: int = 0) -> dict:
    """Search for recipes by meal type."""
    url = f"{BASE_URL}/recipes/complexSearch"
    params = {
        "apiKey": api_key,
        "type": meal_type,           # breakfast, main course, salad, etc.
        "number": number,
        "offset": offset,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,  # includes calories per 100g
        "fillIngredients": True,
        "instructionsRequired": True,
        "sort": "healthiness",
        "sortDirection": "desc",
    }
    if min_health_score > 0:
        params["minHealthScore"] = min_health_score
    r = requests.get(url, params=params, timeout=15)
    _check_quota(r)
    r.raise_for_status()
    return r.json()


def get_recipe_info(api_key: str, recipe_id: int) -> dict:
    """Get full recipe details including nutrition."""
    url = f"{BASE_URL}/recipes/{recipe_id}/information"
    params = {
        "apiKey": api_key,
        "includeNutrition": True,
    }
    r = requests.get(url, params=params, timeout=15)
    _check_quota(r)
    r.raise_for_status()
    return r.json()


def _check_quota(response: requests.Response):
    """Print remaining quota from response headers."""
    left = response.headers.get("X-API-Quota-Left", "?")
    used = response.headers.get("X-API-Quota-Used", "?")
    req_cost = response.headers.get("X-API-Quota-Request", "?")
    print(f"   📊 Quota: used={used}, left={left}, this_request={req_cost}")


# ─── Spoonacular → our schema mapping ────────────────────────────────────────

# Spoonacular meal types → our meal_type values
MEAL_TYPE_MAP = {
    "breakfast":   "breakfast",
    "main course": "dinner",
    "lunch":       "lunch",
    "dinner":      "dinner",
    "salad":       "lunch",
    "soup":        "lunch",
    "snack":       "breakfast",
    "dessert":     "dessert",
}

# Ingredients that disqualify a recipe from the halal tag
_HALAL_UNSAFE_INGREDIENTS = [
    # Pork and derivatives
    "pork", "ham", "bacon", "lard", "prosciutto", "pancetta", "chorizo",
    "guanciale", "mortadella", "coppa", "salami", "pepperoni", "hot_dog",
    "hotdog", "frankfurter", "blood_sausage", "black_pudding",
    # Alcohol
    "wine", "beer", "ale", "lager", "whiskey", "bourbon", "rum", "vodka",
    "sake", "mirin", "brandy", "liqueur", "champagne", "cooking_wine",
    "white_wine", "red_wine", "marsala", "sherry", "vermouth",
    # Blood products
    "blood",
]


def _is_halal_unsafe(ingredient_names: list, title: str) -> bool:
    for name in ingredient_names:
        if any(unsafe in name for unsafe in _HALAL_UNSAFE_INGREDIENTS):
            return True
    return False


# Ingredients that disqualify a recipe from the toddler tag
_TODDLER_UNSAFE_INGREDIENTS = [
    "popcorn", "hot_dog", "hotdog", "frankfurter", "vienna_sausage",
    "salami", "pepperoni", "bologna", "prosciutto", "deli_meat",
    "candy", "lollipop", "gummy",
]
# Whole nuts are unsafe; nut-derived products (butter, milk, flour, oil) are fine
_NUT_NAMES = ["almond", "cashew", "walnut", "pecan", "pistachio", "hazelnut", "macadamia", "brazil_nut", "pine_nut"]
_NUT_SAFE_FORMS = ["butter", "milk", "flour", "oil", "paste", "cream", "extract"]


def _is_toddler_unsafe(ingredient_names: list, title: str) -> bool:
    for name in ingredient_names:
        if any(unsafe in name for unsafe in _TODDLER_UNSAFE_INGREDIENTS):
            return True
        for nut in _NUT_NAMES:
            if nut in name and not any(safe in name for safe in _NUT_SAFE_FORMS):
                return True
        # Whole grapes are a choking hazard; grape juice / grapefruit / grape seed oil are fine
        if name in ("grape", "grapes") or (
            name.startswith("grape_") and not any(s in name for s in ("juice", "seed", "fruit"))
        ):
            return True
    unsafe_title_words = ["popcorn", "candy", "lollipop", "hot dog", "hotdog"]
    return any(w in title for w in unsafe_title_words)


# Spoonacular diet labels → our tags
DIET_TAG_MAP = {
    "vegetarian":    "vegetarian",
    "vegan":         "vegan",
    "gluten free":   "gluten_free",
    "dairy free":    "dairy_free",
    "ketogenic":     "low_carb",
    "paleo":         "paleo",
    "primal":        "paleo",
    "pescetarian":   "no_red_meat",
    "whole30":       "whole30",
}


def _extract_nutrient_per_100g(recipe: dict, nutrient_name: str) -> float:
    """Extract a nutrient (protein/fat/carbs) per 100g from Spoonacular nutrition data."""
    try:
        nutrition = recipe.get("nutrition", {})
        nutrients = nutrition.get("nutrients", [])
        nutrient = next((n for n in nutrients if n.get("name", "").lower() == nutrient_name.lower()), None)
        if not nutrient:
            return 0.0
        amount_per_serving = nutrient.get("amount", 0)
        weight = nutrition.get("weightPerServing", {})
        grams = weight.get("amount", 300) if weight else 300
        unit = weight.get("unit", "").lower() if weight else ""
        if unit == "oz":
            grams = grams * 28.35
        if not grams or grams <= 0:
            grams = 300
        return round((amount_per_serving / grams) * 100, 1)
    except Exception:
        return 0.0


def extract_calories_per_100g(recipe: dict) -> Optional[float]:
    """
    Extract calories per 100g from Spoonacular nutrition data.
    Spoonacular returns calories per serving; we convert using serving weight.
    """
    try:
        nutrition = recipe.get("nutrition", {})
        nutrients = nutrition.get("nutrients", [])

        # Find calories nutrient
        cal_nutrient = next(
            (n for n in nutrients if n.get("name", "").lower() == "calories"), None
        )
        if not cal_nutrient:
            return None

        calories_per_serving = cal_nutrient.get("amount", 0)

        # Get serving weight in grams
        # Spoonacular provides weightPerServing or we can use servingSize
        weight_per_serving = nutrition.get("weightPerServing", {})
        grams = None

        if weight_per_serving:
            grams = weight_per_serving.get("amount", None)
            unit = weight_per_serving.get("unit", "").lower()
            if unit == "oz":
                grams = grams * 28.35 if grams else None
            elif unit not in ("g", "gram", "grams", ""):
                grams = None

        # Fallback: use servings info
        if not grams:
            servings = recipe.get("servings", 1) or 1
            # Estimate: average main dish = 300g/serving
            grams = 300

        if grams and grams > 0:
            return round((calories_per_serving / grams) * 100, 1)

    except Exception:
        pass
    return None


def extract_base_portion_grams(recipe: dict) -> float:
    """Extract serving weight in grams (base portion = 1 serving)."""
    try:
        nutrition = recipe.get("nutrition", {})
        weight = nutrition.get("weightPerServing", {})
        if weight:
            amount = weight.get("amount", 0)
            unit = weight.get("unit", "g").lower()
            if unit in ("g", "gram", "grams", ""):
                return float(amount) if amount else 300.0
            elif unit == "oz":
                return round(float(amount) * 28.35, 1)
    except Exception:
        pass
    return 300.0  # sensible default


def extract_tags(recipe: dict) -> list:
    """Extract dietary tags from Spoonacular recipe."""
    tags = []
    diets = recipe.get("diets", [])
    for diet in diets:
        tag = DIET_TAG_MAP.get(diet.lower())
        if tag and tag not in tags:
            tags.append(tag)

    # Infer no_red_meat from vegetarian/vegan/pescetarian
    if any(t in tags for t in ["vegetarian", "vegan"]):
        if "no_red_meat" not in tags:
            tags.append("no_red_meat")

    # Add high_protein tag if protein is high
    try:
        nutrients = recipe.get("nutrition", {}).get("nutrients", [])
        protein = next((n for n in nutrients if n.get("name") == "Protein"), None)
        if protein and protein.get("amount", 0) > 25:
            tags.append("high_protein")

        # Add high_fiber tag
        fiber = next((n for n in nutrients if n.get("name") == "Fiber"), None)
        if fiber and fiber.get("amount", 0) > 5:
            tags.append("high_fiber")

        # Low spice: if no chili/spicy in title/dish types
        title = recipe.get("title", "").lower()
        spicy_words = ["spicy", "chili", "jalapeño", "habanero", "sriracha", "hot sauce"]
        if not any(w in title for w in spicy_words):
            tags.append("low_spice")

        # Soft food heuristic: soups, porridges, purées
        soft_words = ["soup", "porridge", "oatmeal", "pudding", "smoothie", "puree", "mash"]
        if any(w in title for w in soft_words):
            tags.append("soft_food")

        # Halal: no pork, alcohol, or blood products
        ingredient_names = [
            (ing.get("nameClean") or ing.get("name", "")).lower().replace(" ", "_")
            for ing in recipe.get("extendedIngredients", [])
        ]
        if not _is_halal_unsafe(ingredient_names, title):
            tags.append("halal")

        # Toddler-safe (1-3 years): must be soft + low-spice, halal-safe, and no choking hazards
        if "soft_food" in tags and "low_spice" in tags:
            if not _is_toddler_unsafe(ingredient_names, title) and not _is_halal_unsafe(ingredient_names, title):
                tags.append("toddler")

    except Exception:
        pass

    return list(set(tags))  # deduplicate


def _extract_instructions(recipe: dict) -> str:
    """Extract step-by-step cooking instructions from Spoonacular analyzedInstructions."""
    steps = []
    for group in recipe.get("analyzedInstructions", []):
        for step in group.get("steps", []):
            num = step.get("number", "")
            text = step.get("step", "").strip()
            if text:
                steps.append(f"{num}. {text}")
    return "\n".join(steps) if steps else ""


def extract_ingredients(recipe: dict) -> list:
    """
    Extract ingredients with gram amounts.
    Returns list of (name, grams_per_serving).
    """
    ingredients = []
    extended = recipe.get("extendedIngredients", []) or recipe.get("nutrition", {}).get("ingredients", [])

    for ing in extended:
        name = ing.get("nameClean") or ing.get("name", "")
        if not name:
            continue

        # Normalize name: lowercase, replace spaces with underscores
        name = name.lower().strip().replace(" ", "_")

        # Get grams
        measures = ing.get("measures", {})
        metric = measures.get("metric", {})
        grams = metric.get("amount", None)
        unit = metric.get("unitShort", "").lower()

        if grams is None:
            # Try direct amount field
            grams = ing.get("amount", 50)
            unit = ing.get("unit", "g").lower()

        # Convert to grams
        if unit in ("g", "gram", "grams", ""):
            grams = float(grams)
        elif unit in ("kg", "kilogram"):
            grams = float(grams) * 1000
        elif unit in ("oz", "ounce"):
            grams = float(grams) * 28.35
        elif unit in ("lb", "pound"):
            grams = float(grams) * 453.6
        elif unit in ("ml", "milliliter", "millilitre"):
            grams = float(grams)  # ~1g/ml approximation
        elif unit in ("l", "liter", "litre"):
            grams = float(grams) * 1000
        elif unit in ("tbsp", "tablespoon"):
            grams = float(grams) * 15
        elif unit in ("tsp", "teaspoon"):
            grams = float(grams) * 5
        elif unit in ("cup",):
            grams = float(grams) * 240
        else:
            grams = float(grams) if grams else 50  # fallback

        if grams > 0:
            ingredients.append((name, round(grams, 1)))

    return ingredients


def map_meal_type(recipe: dict) -> str:
    """Map Spoonacular dish types to our breakfast/lunch/dinner."""
    dish_types = [t.lower() for t in recipe.get("dishTypes", [])]
    for dt in dish_types:
        if dt in MEAL_TYPE_MAP:
            return MEAL_TYPE_MAP[dt]
    return "dinner"  # safe default


# ─── Main seeder ─────────────────────────────────────────────────────────────

def seed_from_spoonacular(api_key: str, target_count: int = 150, delay: float = 0.5, min_health_score: int = 0):
    """
    Fetch recipes from Spoonacular and seed the DB.

    Strategy:
    - Fetch from 3 meal types: breakfast, main course, lunch
    - Spread requests to avoid hitting quota
    - Skip duplicates (by name)
    """
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing_names = {r.name.lower() for r in db.query(models.Recipe).all()}
    print(f"📚 Existing recipes in DB: {len(existing_names)}")

    per_type = {
        "breakfast":   target_count // 5,
        "main course": target_count // 5,
        "lunch":       target_count // 5,
        "salad":       target_count // 5,
        "dessert":     target_count - 4 * (target_count // 5),
    }

    added = 0
    errors = 0

    for spoon_type, count in per_type.items():
        our_type = MEAL_TYPE_MAP[spoon_type]
        print(f"\n🍽️  Fetching {count} '{spoon_type}' recipes → stored as '{our_type}'")

        offset = 0
        fetched_this_type = 0
        BATCH = 10  # stay conservative with free tier

        while fetched_this_type < count:
            batch_size = min(BATCH, count - fetched_this_type)
            print(f"  Fetching offset={offset}, batch={batch_size}...")

            try:
                result = search_recipes(api_key, spoon_type, offset=offset, number=batch_size, min_health_score=min_health_score)
                recipes_data = result.get("results", [])

                if not recipes_data:
                    print(f"  ⚠️  No more results for {spoon_type}")
                    break

                for recipe_data in recipes_data:
                    name = recipe_data.get("title", "")
                    if not name or name.lower() in existing_names:
                        print(f"    ⏭️  Skipping duplicate: {name}")
                        continue

                    # complexSearch sometimes omits analyzedInstructions —
                    # fetch full recipe info to guarantee we get the steps
                    if not recipe_data.get("analyzedInstructions"):
                        recipe_id = recipe_data.get("id")
                        if recipe_id:
                            try:
                                recipe_data = get_recipe_info(api_key, recipe_id)
                                time.sleep(delay)
                            except Exception as e:
                                print(f"    ⚠️  Could not fetch full info for '{name}': {e}")

                    try:
                        recipe_obj = _save_recipe(db, recipe_data, our_type)
                        if recipe_obj:
                            existing_names.add(name.lower())
                            added += 1
                            fetched_this_type += 1
                            print(f"    ✅ [{added}] {name}")
                    except Exception as e:
                        errors += 1
                        print(f"    ❌ Failed to save '{name}': {e}")

                    time.sleep(delay)  # be polite to the API

                offset += batch_size

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 402:
                    print("  ⛔ Daily quota exhausted! Run again tomorrow.")
                    db.close()
                    return
                raise

            time.sleep(delay * 2)  # extra pause between batches

    db.close()
    print(f"\n✅ Done! Added {added} recipes. Errors: {errors}")
    print(f"📊 Total recipes in DB: {len(existing_names)}")


def _save_recipe(db, recipe_data: dict, meal_type: str):
    """Parse one Spoonacular recipe and save to DB."""
    name = recipe_data.get("title", "").strip()
    if not name:
        return None

    # Get calories per 100g
    cal_per_100g = extract_calories_per_100g(recipe_data)
    if not cal_per_100g or cal_per_100g <= 0:
        cal_per_100g = 120.0  # safe fallback

    # Clamp to reasonable range
    cal_per_100g = max(30.0, min(cal_per_100g, 600.0))

    base_portion_grams = extract_base_portion_grams(recipe_data)
    base_portion_grams = max(100.0, min(base_portion_grams, 800.0))

    import re
    description = recipe_data.get("summary", "")
    description = re.sub(r"<[^>]+>", "", description)[:300] if description else ""

    # Extract step-by-step cooking instructions
    cooking_instructions = _extract_instructions(recipe_data)

    recipe = models.Recipe(
        name=name,
        meal_type=meal_type,
        base_portion_grams=base_portion_grams,
        calories_per_100g=cal_per_100g,
        protein_per_100g=_extract_nutrient_per_100g(recipe_data, "Protein"),
        fat_per_100g=_extract_nutrient_per_100g(recipe_data, "Fat"),
        carbs_per_100g=_extract_nutrient_per_100g(recipe_data, "Carbohydrates"),
        description=description,
        cooking_instructions=cooking_instructions,
        source="spoonacular",
    )
    db.add(recipe)
    db.flush()

    # Tags
    tags = extract_tags(recipe_data)
    for tag in tags:
        db.add(models.RecipeTag(recipe_id=recipe.id, tag=tag))

    # Ingredients
    ingredients = extract_ingredients(recipe_data)
    for ing_name, grams in ingredients:
        db.add(models.RecipeIngredient(
            recipe_id=recipe.id,
            name=ing_name,
            grams_per_base_portion=grams,
        ))

    db.commit()
    return recipe


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed meal planner DB from Spoonacular API")
    parser.add_argument("--api-key", required=True, help="Your Spoonacular API key")
    parser.add_argument("--count", type=int, default=150, help="Total recipes to fetch (default 150)")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between requests (default 0.5)")
    parser.add_argument("--min-health-score", type=int, default=0, help="Minimum Spoonacular health score 0-100 (default 0 = no filter). Use 60+ for healthy recipes.")
    args = parser.parse_args()

    print(f"🚀 Seeding DB from Spoonacular (target: {args.count} recipes)")
    print(f"   Free tier tip: stay under 100-120 recipes/day to avoid quota issues\n")

    seed_from_spoonacular(
        api_key=args.api_key,
        target_count=args.count,
        delay=args.delay,
        min_health_score=args.min_health_score,
    )
