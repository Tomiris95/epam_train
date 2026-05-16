"""
Deterministic calorie and portion engine.
NO LLM involved — pure math.
"""
from typing import List, Dict
from backend.models import FamilyMember, Recipe

# Meal calorie splits
MEAL_SPLITS = {
    "breakfast": 0.30,
    "lunch": 0.40,
    "dinner": 0.30,
}

# Acceptable deviation from a member's daily calorie target (kcal)
CALORIE_TOLERANCE = 100.0


def compute_portion(recipe: Recipe, target_meal_calories: float) -> Dict:
    """
    Given a recipe and a calorie target for a meal slot,
    compute the adjusted grams for this member.
    Returns dict with grams, calories, and macros.
    """
    cal_per_portion = (recipe.base_portion_grams / 100.0) * recipe.calories_per_100g
    if cal_per_portion <= 0:
        coef = 1.0
    else:
        coef = target_meal_calories / cal_per_portion

    adjusted_grams = recipe.base_portion_grams * coef
    actual_calories = (adjusted_grams / 100.0) * recipe.calories_per_100g
    actual_protein  = (adjusted_grams / 100.0) * (recipe.protein_per_100g or 0.0)
    actual_fat      = (adjusted_grams / 100.0) * (recipe.fat_per_100g or 0.0)
    actual_carbs    = (adjusted_grams / 100.0) * (recipe.carbs_per_100g or 0.0)

    return {
        "adjusted_grams":  round(adjusted_grams, 1),
        "actual_calories": round(actual_calories, 1),
        "actual_protein":  round(actual_protein, 1),
        "actual_fat":      round(actual_fat, 1),
        "actual_carbs":    round(actual_carbs, 1),
        "coef":            round(coef, 3),
    }


def compute_member_portions(
    member: FamilyMember,
    breakfast: Recipe,
    lunch: Recipe,
    dinner: Recipe,
) -> Dict:
    """
    Compute portions for a single family member for all three meals.
    Returns per-meal grams, calories, macros, and daily totals.
    """
    target = member.calorie_target
    portions = {}
    total_cal = total_protein = total_fat = total_carbs = 0.0

    for meal_type, recipe in [("breakfast", breakfast), ("lunch", lunch), ("dinner", dinner)]:
        meal_target = target * MEAL_SPLITS[meal_type]
        p = compute_portion(recipe, meal_target)
        portions[meal_type] = p
        total_cal     += p["actual_calories"]
        total_protein += p["actual_protein"]
        total_fat     += p["actual_fat"]
        total_carbs   += p["actual_carbs"]

    return {
        "member_id":        member.id,
        "member_name":      member.name,
        "calorie_target":   target,
        "breakfast_grams":    portions["breakfast"]["adjusted_grams"],
        "breakfast_calories": portions["breakfast"]["actual_calories"],
        "lunch_grams":        portions["lunch"]["adjusted_grams"],
        "lunch_calories":     portions["lunch"]["actual_calories"],
        "dinner_grams":       portions["dinner"]["adjusted_grams"],
        "dinner_calories":    portions["dinner"]["actual_calories"],
        "total_calories": round(total_cal, 1),
        "total_protein":  round(total_protein, 1),
        "total_fat":      round(total_fat, 1),
        "total_carbs":    round(total_carbs, 1),
    }


def validate_daily_calories(member_portions: Dict, tolerance: float = CALORIE_TOLERANCE) -> bool:
    """Returns True if actual total is within ±tolerance of calorie_target."""
    diff = abs(member_portions["total_calories"] - member_portions["calorie_target"])
    return diff <= tolerance


def compute_all_members_portions(
    members: List[FamilyMember],
    breakfast: Recipe,
    lunch: Recipe,
    dinner: Recipe,
) -> List[Dict]:
    """Compute portions for all family members."""
    return [compute_member_portions(m, breakfast, lunch, dinner) for m in members]
