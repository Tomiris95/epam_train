"""
Agent 3: Planner Agent
Input:  preference_result, list of members, db session, optional fridge items
Output: selected breakfast/lunch/dinner recipes + member portions
        Regenerates if calorie constraint violated (±100 kcal).
"""
import logging
import random
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models import FamilyMember, Recipe
from backend.agents.recipe_agent import RecipeAgent
from backend.engine.calorie_engine import compute_all_members_portions, validate_daily_calories

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
TOP_K_CANDIDATES = 30


class PlannerAgent:
    """
    Orchestrates the daily meal plan:
    1. Calls RecipeAgent for each meal slot
    2. Picks best-fit recipe
    3. Validates calorie constraints via CalorieEngine
    4. Regenerates if constraints violated
    """

    def __init__(self):
        self.recipe_agent = RecipeAgent()

    def run(
        self,
        db: Session,
        preference_result: Dict,
        members: List[FamilyMember],
        fridge_items: Optional[List[str]] = None,
        disliked_ids: Optional[List[int]] = None,
    ) -> Dict:
        """
        Generate a complete daily meal plan.
        Returns: {
            breakfast: Recipe,
            lunch: Recipe,
            dinner: Recipe,
            member_portions: List[Dict],
            retries: int,
        }
        """
        fridge = set(item.lower() for item in (fridge_items or []))
        disliked = list(disliked_ids or [])
        best_plan = None
        best_score = float("inf")

        for attempt in range(MAX_RETRIES):
            breakfast, lunch, dinner = self._pick_meals(
                db=db,
                preference_result=preference_result,
                fridge=fridge,
                attempt=attempt,
                disliked_ids=disliked,
            )

            missing = [m for m, r in [("breakfast", breakfast), ("lunch", lunch), ("dinner", dinner)] if not r]
            if missing:
                logger.warning("Attempt %d: no recipes found for %s.", attempt + 1, missing)
                continue

            member_portions = compute_all_members_portions(members, breakfast, lunch, dinner)

            # Validate calorie constraints for all members
            all_valid = all(validate_daily_calories(mp) for mp in member_portions)

            # Track total deviation for best-plan selection
            total_deviation = sum(
                abs(mp["total_calories"] - mp["calorie_target"]) for mp in member_portions
            )

            logger.info(
                "Attempt %d: %s / %s / %s | deviation=%.1f | valid=%s",
                attempt + 1, breakfast.name, lunch.name, dinner.name,
                total_deviation, all_valid,
            )

            if all_valid:
                best_plan = (breakfast, lunch, dinner, member_portions, attempt + 1)
                break

            if total_deviation < best_score:
                best_score = total_deviation
                best_plan = (breakfast, lunch, dinner, member_portions, attempt + 1)

        if best_plan is None:
            total_recipes = db.query(Recipe).count()
            if total_recipes == 0:
                raise ValueError("No recipes in the database. Run seed_from_epub.py or spoonacular_seed.py first.")
            raise ValueError(
                f"Could not find recipes for all meal slots after {MAX_RETRIES} attempts. "
                f"DB has {total_recipes} recipes — dietary constraints may be too strict."
            )

        breakfast, lunch, dinner, member_portions, retries = best_plan

        return {
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
            "member_portions": member_portions,
            "retries": retries,
        }

    def _pick_meals(
        self,
        db: Session,
        preference_result: Dict,
        fridge: set,
        attempt: int,
        disliked_ids: Optional[List[int]] = None,
    ) -> Tuple[Optional[Recipe], Optional[Recipe], Optional[Recipe]]:
        """Pick one recipe for each meal slot."""
        meals = {}
        selected_ids = []   # IDs of recipes already picked for earlier slots
        disliked = list(disliked_ids or [])

        for meal_type in ["breakfast", "lunch", "dinner"]:
            # First try: exclude both already-selected and disliked recipes
            candidates = self.recipe_agent.run(
                db=db,
                preference_result=preference_result,
                meal_type=meal_type,
                top_k=TOP_K_CANDIDATES,
                exclude_recipe_ids=selected_ids + disliked,
            )

            # Soft fallback: if nothing found, allow disliked recipes
            if not candidates and disliked:
                logger.warning(
                    "No candidates for %s after excluding %d disliked recipes — falling back to full pool.",
                    meal_type, len(disliked),
                )
                candidates = self.recipe_agent.run(
                    db=db,
                    preference_result=preference_result,
                    meal_type=meal_type,
                    top_k=TOP_K_CANDIDATES,
                    exclude_recipe_ids=selected_ids,
                )

            if not candidates:
                meals[meal_type] = None
                continue

            # Score recipes by fridge coverage (prefer recipes using fridge items)
            scored = []
            for recipe in candidates:
                recipe_ings = {i.name.lower() for i in recipe.ingredients}
                fridge_overlap = len(recipe_ings & fridge)
                total_ings = len(recipe_ings)
                fridge_score = fridge_overlap / max(total_ings, 1)
                scored.append((fridge_score, recipe))

            # Sort by fridge score descending
            scored.sort(key=lambda x: x[0], reverse=True)

            # If fridge is empty (all scores = 0), all candidates are equally good —
            # pick randomly from the whole pool for variety.
            # Otherwise favour fridge-overlap but still grow the pool on retries.
            best_score = scored[0][0] if scored else 0
            if best_score == 0:
                chosen = random.choice(scored)[1]
            else:
                pool_size = max(1, min(len(scored), 5 + attempt * 2))
                chosen = random.choice(scored[:pool_size])[1]

            meals[meal_type] = chosen
            selected_ids.append(chosen.id)

        return meals.get("breakfast"), meals.get("lunch"), meals.get("dinner")

    def replace_meal(
        self,
        db: Session,
        preference_result: Dict,
        members: List[FamilyMember],
        meal_type: str,
        current_recipe_id: int,
        other_recipes: Dict[str, Recipe],  # the other two meal recipes keeping
        preference: str = "",
        disliked_ids: Optional[List[int]] = None,
    ) -> Dict:
        """
        Replace a single meal slot with an alternative recipe.
        Validates calorie constraints.
        """
        alternatives = self.recipe_agent.get_alternatives(
            db=db,
            preference_result=preference_result,
            meal_type=meal_type,
            exclude_recipe_id=current_recipe_id,
            limit=10,
            query_hint=preference,
            disliked_ids=disliked_ids,
        )

        # Soft fallback: if nothing found excluding disliked, allow them
        if not alternatives and disliked_ids:
            logger.warning(
                "No alternatives for %s after excluding %d disliked recipes — falling back to full pool.",
                meal_type, len(disliked_ids),
            )
            alternatives = self.recipe_agent.get_alternatives(
                db=db,
                preference_result=preference_result,
                meal_type=meal_type,
                exclude_recipe_id=current_recipe_id,
                limit=10,
                query_hint=preference,
                disliked_ids=None,
            )

        if not alternatives:
            raise ValueError(f"No alternative recipes found for {meal_type}.")

        breakfast = other_recipes.get("breakfast")
        lunch = other_recipes.get("lunch")
        dinner = other_recipes.get("dinner")

        best = None
        best_deviation = float("inf")

        for alt in alternatives:
            meals = {"breakfast": breakfast, "lunch": lunch, "dinner": dinner}
            meals[meal_type] = alt
            portions = compute_all_members_portions(
                members, meals["breakfast"], meals["lunch"], meals["dinner"]
            )
            deviation = sum(abs(mp["total_calories"] - mp["calorie_target"]) for mp in portions)
            if deviation < best_deviation:
                best_deviation = deviation
                best = (alt, portions)

        if best is None:
            best = (alternatives[0], compute_all_members_portions(
                members, breakfast, lunch, dinner
            ))

        alt_recipe, member_portions = best
        logger.info("Replaced %s with '%s' (deviation=%.1f)", meal_type, alt_recipe.name, best_deviation)

        return {
            "recipe": alt_recipe,
            "member_portions": member_portions,
        }
