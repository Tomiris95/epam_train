"""
Calorie engine unit tests — pure math, no DB or HTTP.
"""
import pytest
from unittest.mock import MagicMock
from backend.engine.calorie_engine import (
    compute_portion,
    compute_member_portions,
    validate_daily_calories,
    CALORIE_TOLERANCE,
)


def _make_recipe(base_grams=300.0, cal_per_100g=100.0,
                 protein=10.0, fat=5.0, carbs=20.0):
    r = MagicMock()
    r.base_portion_grams = base_grams
    r.calories_per_100g = cal_per_100g
    r.protein_per_100g = protein
    r.fat_per_100g = fat
    r.carbs_per_100g = carbs
    return r


def _make_member(calorie_target=2000):
    m = MagicMock()
    m.id = 1
    m.name = "Alice"
    m.calorie_target = calorie_target
    return m


# ─── compute_portion ──────────────────────────────────────────────────────────

def test_compute_portion_exact_target():
    recipe = _make_recipe(base_grams=300.0, cal_per_100g=100.0)
    # base portion = 300g → 300 kcal; target = 300 kcal → coef = 1.0
    result = compute_portion(recipe, 300.0)
    assert result["adjusted_grams"] == pytest.approx(300.0, abs=0.1)
    assert result["actual_calories"] == pytest.approx(300.0, abs=0.1)


def test_compute_portion_scales_up():
    recipe = _make_recipe(base_grams=100.0, cal_per_100g=200.0)
    # base portion = 100g → 200 kcal; target = 400 kcal → coef = 2.0
    result = compute_portion(recipe, 400.0)
    assert result["adjusted_grams"] == pytest.approx(200.0, abs=0.1)
    assert result["actual_calories"] == pytest.approx(400.0, abs=0.1)


def test_compute_portion_scales_down():
    recipe = _make_recipe(base_grams=500.0, cal_per_100g=100.0)
    # base portion = 500g → 500 kcal; target = 250 kcal → coef = 0.5
    result = compute_portion(recipe, 250.0)
    assert result["adjusted_grams"] == pytest.approx(250.0, abs=0.1)
    assert result["actual_calories"] == pytest.approx(250.0, abs=0.1)


def test_compute_portion_zero_cal_recipe_uses_coef_1():
    recipe = _make_recipe(base_grams=300.0, cal_per_100g=0.0)
    result = compute_portion(recipe, 300.0)
    assert result["adjusted_grams"] == pytest.approx(300.0, abs=0.1)


def test_compute_portion_includes_macros():
    recipe = _make_recipe(base_grams=100.0, cal_per_100g=100.0,
                           protein=20.0, fat=10.0, carbs=30.0)
    result = compute_portion(recipe, 100.0)  # coef = 1.0
    assert result["actual_protein"] == pytest.approx(20.0, abs=0.1)
    assert result["actual_fat"] == pytest.approx(10.0, abs=0.1)
    assert result["actual_carbs"] == pytest.approx(30.0, abs=0.1)


# ─── compute_member_portions ─────────────────────────────────────────────────

def test_compute_member_portions_sums_correctly():
    member = _make_member(calorie_target=2000)
    breakfast = _make_recipe(base_grams=300.0, cal_per_100g=100.0)  # 300 kcal base
    lunch     = _make_recipe(base_grams=400.0, cal_per_100g=100.0)  # 400 kcal base
    dinner    = _make_recipe(base_grams=300.0, cal_per_100g=100.0)  # 300 kcal base

    result = compute_member_portions(member, breakfast, lunch, dinner)

    assert result["member_name"] == "Alice"
    assert result["calorie_target"] == 2000
    assert result["total_calories"] == pytest.approx(2000.0, abs=5.0)


def test_compute_member_portions_applies_meal_splits():
    member = _make_member(calorie_target=2000)
    recipe = _make_recipe(base_grams=300.0, cal_per_100g=100.0)

    result = compute_member_portions(member, recipe, recipe, recipe)

    # Breakfast = 30% of 2000 = 600 kcal
    assert result["breakfast_grams"] == pytest.approx(600.0, abs=1.0)
    # Lunch = 40% of 2000 = 800 kcal
    assert result["lunch_grams"] == pytest.approx(800.0, abs=1.0)
    # Dinner = 30% of 2000 = 600 kcal
    assert result["dinner_grams"] == pytest.approx(600.0, abs=1.0)


# ─── validate_daily_calories ─────────────────────────────────────────────────

def test_validate_passes_within_tolerance():
    portions = {"total_calories": 2050.0, "calorie_target": 2000}
    assert validate_daily_calories(portions) is True


def test_validate_fails_above_tolerance():
    portions = {"total_calories": 2200.0, "calorie_target": 2000}
    assert validate_daily_calories(portions) is False


def test_validate_fails_below_tolerance():
    portions = {"total_calories": 1800.0, "calorie_target": 2000}
    assert validate_daily_calories(portions) is False


def test_validate_passes_at_exact_tolerance_boundary():
    portions = {"total_calories": 2000.0 + CALORIE_TOLERANCE, "calorie_target": 2000}
    assert validate_daily_calories(portions) is True
