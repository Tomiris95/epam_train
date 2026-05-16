"""
Shopping list generator — returns ALL ingredients from the meal plan recipes,
scaled to the actual portions for each family member.
Fridge items are NOT subtracted here; they are used only by the PlannerAgent
to score/prefer recipes that use available ingredients.
"""
from typing import List, Dict
from backend.models import Recipe

# Nutritional macro words that should never appear as shopping items
_NON_FOOD = {
    "белки", "белок", "жиры", "жир", "углеводы", "углевод", "углеводов",
    "калории", "ккал", "калорий", "калория",
    "protein", "proteins", "fat", "fats", "carbs", "carbohydrates",
    "calories", "kcal", "energy",
}


def _canonical_key(name: str) -> str:
    """Sort words so 'Грудка Куриная' and 'Куриная Грудка' map to the same key.
    Null byte as separator: it never appears in ingredient names so it cannot
    accidentally bridge two separate words into a false match."""
    return "\x00".join(sorted(name.lower().strip().split()))


def _is_non_food(name: str) -> bool:
    words = set(name.lower().split())
    return bool(words & _NON_FOOD)


def generate_shopping_list(
    recipes: List[Recipe],
    member_count: int,
    member_portions: List[Dict],
) -> List[Dict]:
    """
    Returns a list of {ingredient, grams_needed} for every ingredient in the plan.
    Grams are scaled by each member's actual portion vs the recipe base portion.
    Duplicate ingredients (different word order) are merged by canonical key.
    """
    # key → {display_name, grams}
    shopping: Dict[str, Dict] = {}

    for recipe in recipes:
        meal_type = recipe.meal_type

        # Average portion coefficient across all members for this meal
        coefs = []
        for mp in member_portions:
            if meal_type == "breakfast":
                grams = mp.get("breakfast_grams", recipe.base_portion_grams)
            elif meal_type == "lunch":
                grams = mp.get("lunch_grams", recipe.base_portion_grams)
            else:
                grams = mp.get("dinner_grams", recipe.base_portion_grams)
            coef = grams / recipe.base_portion_grams if recipe.base_portion_grams > 0 else 1.0
            coefs.append(coef)

        avg_coef = sum(coefs) / len(coefs) if coefs else 1.0

        for ingredient in recipe.ingredients:
            raw_name = ingredient.name.strip()
            if _is_non_food(raw_name):
                continue

            key = _canonical_key(raw_name)
            total_grams = ingredient.grams_per_base_portion * avg_coef * member_count

            if key in shopping:
                shopping[key]["grams"] += total_grams
            else:
                shopping[key] = {"display": raw_name, "grams": total_grams}

    return [
        {"ingredient": v["display"], "grams_needed": round(v["grams"], 1)}
        for v in sorted(shopping.values(), key=lambda x: x["display"].lower())
    ]
