"""
Shopping engine unit tests — deduplication, non-food filtering, grams scaling.
No DB or HTTP needed.
"""
import pytest
from unittest.mock import MagicMock
from backend.engine.shopping_engine import generate_shopping_list


def _make_ingredient(name, grams):
    i = MagicMock()
    i.name = name
    i.grams_per_base_portion = grams
    return i


def _make_recipe(meal_type, base_grams, cal_per_100g, ingredients):
    r = MagicMock()
    r.meal_type = meal_type
    r.base_portion_grams = base_grams
    r.calories_per_100g = cal_per_100g
    r.ingredients = [_make_ingredient(n, g) for n, g in ingredients]
    return r


def _portions(meal_type, grams, base_grams=300.0):
    return {
        "breakfast_grams": grams if meal_type == "breakfast" else base_grams,
        "lunch_grams": grams if meal_type == "lunch" else base_grams,
        "dinner_grams": grams if meal_type == "dinner" else base_grams,
    }


# ─── Positive ─────────────────────────────────────────────────────────────────

def test_basic_shopping_list_generated():
    recipe = _make_recipe("breakfast", 300.0, 100.0, [("Oats", 100.0), ("Milk", 200.0)])
    member_portions = [_portions("breakfast", 300.0)]
    result = generate_shopping_list([recipe], member_count=1, member_portions=member_portions)
    names = [item["ingredient"] for item in result]
    assert "Oats" in names
    assert "Milk" in names


def test_grams_scaled_by_member_count():
    recipe = _make_recipe("lunch", 300.0, 100.0, [("Rice", 150.0)])
    member_portions = [_portions("lunch", 300.0)]
    result = generate_shopping_list([recipe], member_count=2, member_portions=member_portions)
    rice = next(i for i in result if i["ingredient"] == "Rice")
    # 150g × coef(1.0) × 2 members = 300g
    assert rice["grams_needed"] == pytest.approx(300.0, abs=1.0)


def test_duplicate_ingredient_word_order_merged():
    """'Грудка Куриная' and 'Куриная Грудка' must be merged into one entry."""
    r1 = _make_recipe("breakfast", 300.0, 100.0, [("Грудка Куриная", 100.0)])
    r2 = _make_recipe("lunch",     300.0, 100.0, [("Куриная Грудка", 100.0)])
    portions = [{"breakfast_grams": 300.0, "lunch_grams": 300.0, "dinner_grams": 300.0}]
    result = generate_shopping_list([r1, r2], member_count=1, member_portions=portions)
    chicken_items = [
        item for item in result
        if "грудка" in item["ingredient"].lower() or "куриная" in item["ingredient"].lower()
    ]
    assert len(chicken_items) == 1
    assert chicken_items[0]["grams_needed"] == pytest.approx(200.0, abs=1.0)


def test_multiple_recipes_all_included():
    breakfast = _make_recipe("breakfast", 300.0, 100.0, [("Egg",  50.0)])
    lunch     = _make_recipe("lunch",     300.0, 100.0, [("Rice", 150.0)])
    dinner    = _make_recipe("dinner",    300.0, 100.0, [("Fish", 200.0)])
    portions  = [{"breakfast_grams": 300.0, "lunch_grams": 300.0, "dinner_grams": 300.0}]
    result    = generate_shopping_list([breakfast, lunch, dinner], 1, portions)
    names     = [i["ingredient"] for i in result]
    assert "Egg" in names
    assert "Rice" in names
    assert "Fish" in names


def test_empty_recipe_list_returns_empty():
    result = generate_shopping_list([], member_count=1, member_portions=[])
    assert result == []


# ─── Negative ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_ingredient", [
    "Белки", "Жиры", "Углеводы", "Ккал", "Калории",
    "protein", "fat", "carbs", "calories", "kcal",
])
def test_non_food_macro_words_filtered(bad_ingredient):
    recipe = _make_recipe("lunch", 300.0, 100.0, [(bad_ingredient, 50.0)])
    portions = [{"breakfast_grams": 300.0, "lunch_grams": 300.0, "dinner_grams": 300.0}]
    result = generate_shopping_list([recipe], member_count=1, member_portions=portions)
    names = [i["ingredient"].lower() for i in result]
    assert bad_ingredient.lower() not in names
