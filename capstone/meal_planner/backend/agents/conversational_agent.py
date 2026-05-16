"""
Conversational Agent — LLM-based meal plan adjuster.
Uses OpenAI GPT-4o with function calling to interpret natural language requests
and call the existing PlannerAgent.replace_meal when needed.
"""
import json
import logging
import os
import time
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

load_dotenv()

from backend import models
from backend.agents.preference_agent import PreferenceAgent
from backend.agents.planner_agent import PlannerAgent

MODEL = "gpt-4o"

# GPT-4o pricing — override via env vars if pricing changes
_INPUT_COST_PER_1K  = float(os.getenv("GPT4O_INPUT_COST_PER_1K",  "0.005"))
_OUTPUT_COST_PER_1K = float(os.getenv("GPT4O_OUTPUT_COST_PER_1K", "0.015"))


def _estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        prompt_tokens / 1000 * _INPUT_COST_PER_1K +
        completion_tokens / 1000 * _OUTPUT_COST_PER_1K,
        5,
    )

REPLACEMENT_KEYWORDS = {
    # English
    "replace", "swap", "change", "switch", "different", "instead",
    # Russian
    "поменяй", "замени", "измени", "смени", "перемени", "другой", "другое", "другую",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "replace_meal",
            "description": (
                "Replace a meal slot (breakfast, lunch, or dinner) with an alternative recipe "
                "that better matches the user's request. Use this when the user asks to swap, "
                "change, or replace a specific meal, or expresses dissatisfaction with one."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner"],
                        "description": "Which meal slot to replace.",
                    },
                    "preference": {
                        "type": "string",
                        "description": "Ingredient or style the user wants, e.g. 'chicken', 'курица', 'something light'. Can be in any language.",
                    },
                },
                "required": ["meal_type"],
            },
        },
    }
]


class ConversationalAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.preference_agent = PreferenceAgent()
        self.planner_agent = PlannerAgent()

    def run(
        self,
        db: Session,
        plan: models.MealPlan,
        user_message: str,
        chat_history: List[Dict],
        disliked_ids: Optional[List[int]] = None,
    ) -> Dict:
        """
        Process a user message about the current meal plan.

        chat_history: list of {"role": "user"|"assistant", "content": str}
        Returns: {"response": str, "updated_plan": dict | None}
        """
        family = plan.family
        members = family.members
        pref_result = self.preference_agent.run(members)
        items = {item.meal_type: item.recipe for item in plan.items}

        system_prompt = self._build_system_prompt(items, members, pref_result)
        messages = (
            [{"role": "system", "content": system_prompt}]
            + list(chat_history)
            + [{"role": "user", "content": user_message}]
        )

        wants_replace = self._wants_replacement(user_message)
        # "required" forces a tool call before any text is generated, preventing
        # the hallucination pattern where GPT-4o describes a replacement it never executed.
        tool_choice = "required" if wants_replace else "auto"

        t0 = time.perf_counter()
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice=tool_choice,
        )
        u = response.usage
        cost1 = _estimate_cost(u.prompt_tokens, u.completion_tokens)
        logger.info(
            "OpenAI call 1 (tool_choice=%s): %.2fs | tokens: prompt=%d completion=%d total=%d | est. cost=$%.5f",
            tool_choice, time.perf_counter() - t0, u.prompt_tokens, u.completion_tokens, u.total_tokens, cost1,
        )

        assistant_message = response.choices[0].message
        updated_plan_data = None
        total_tokens = u.total_tokens

        if not assistant_message.tool_calls and wants_replace:
            logger.warning("ConversationalAgent: replacement requested but no tool call made — returning safe fallback")
            logger.info("ConversationalAgent turn total tokens: %d", total_tokens)
            return {
                "response": "I couldn't find a suitable replacement right now. Try being more specific, e.g. \"Replace dinner with something with salmon\".",
                "updated_plan": None,
            }

        if assistant_message.tool_calls:
            messages.append(assistant_message)

            for tool_call in assistant_message.tool_calls:
                if tool_call.function.name != "replace_meal":
                    continue

                args = json.loads(tool_call.function.arguments)
                meal_type = args["meal_type"]
                preference = args.get("preference", "")
                current_recipe = items.get(meal_type)
                other_recipes = {mt: r for mt, r in items.items() if mt != meal_type}

                try:
                    result = self.planner_agent.replace_meal(
                        db=db,
                        preference_result=pref_result,
                        members=members,
                        meal_type=meal_type,
                        current_recipe_id=current_recipe.id,
                        other_recipes=other_recipes,
                        preference=preference,
                        disliked_ids=disliked_ids,
                    )

                    for plan_item in plan.items:
                        if plan_item.meal_type == meal_type:
                            plan_item.recipe_id = result["recipe"].id
                            break
                    db.commit()
                    db.refresh(plan)

                    items[meal_type] = result["recipe"]
                    updated_plan_data = result

                    new_recipe = result["recipe"]
                    new_tags = [t.tag for t in new_recipe.tags]
                    tool_result_content = (
                        f"Replaced {meal_type} with '{new_recipe.name}' "
                        f"({new_recipe.calories_per_100g} kcal/100g, "
                        f"{new_recipe.base_portion_grams}g base portion). "
                        f"Tags: {', '.join(new_tags) or 'none'}."
                    )

                except Exception as e:
                    tool_result_content = f"Failed to replace {meal_type}: {e}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result_content,
                })

            # Second call: generate the user-facing text response from the tool result.
            # tool_choice="none" prevents the model from calling the tool again.
            t1 = time.perf_counter()
            follow_up = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="none",
            )
            u2 = follow_up.usage
            total_tokens += u2.total_tokens
            cost2 = _estimate_cost(u2.prompt_tokens, u2.completion_tokens)
            logger.info(
                "OpenAI call 2: %.2fs | tokens: prompt=%d completion=%d total=%d | est. cost=$%.5f",
                time.perf_counter() - t1, u2.prompt_tokens, u2.completion_tokens, u2.total_tokens, cost2,
            )
            total_cost = cost1 + cost2
            logger.info(
                "ConversationalAgent turn total tokens: %d | total est. cost=$%.5f",
                total_tokens, total_cost,
            )
            text_response = follow_up.choices[0].message.content

        else:
            total_cost = cost1
            logger.info(
                "ConversationalAgent turn total tokens: %d | total est. cost=$%.5f",
                total_tokens, total_cost,
            )
            text_response = assistant_message.content

        return {
            "response": text_response,
            "updated_plan": updated_plan_data,
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_cost,
        }

    def _wants_replacement(self, user_message: str) -> bool:
        lower = user_message.lower()
        return any(kw in lower for kw in REPLACEMENT_KEYWORDS)

    def _build_system_prompt(self, items: dict, members, pref_result: dict) -> str:
        plan_lines = []
        for meal_type in ["breakfast", "lunch", "dinner"]:
            recipe = items.get(meal_type)
            if recipe:
                tags = [t.tag for t in recipe.tags]
                ings = [i.name for i in recipe.ingredients[:6]]
                plan_lines.append(
                    f"- {meal_type.capitalize()}: {recipe.name} "
                    f"| {recipe.calories_per_100g} kcal/100g, {recipe.base_portion_grams}g base "
                    f"| Tags: {', '.join(tags) or 'none'} "
                    f"| Ingredients: {', '.join(ings)}"
                )

        member_lines = []
        for m in members:
            m_tags = [dt.tag for dt in m.diet_tags]
            member_lines.append(f"- {m.name}: {m.age}y, {m.calorie_target} kcal/day, tags: {m_tags}")

        return f"""You are a friendly meal planning assistant helping a family adjust their daily meal plan.

Current meal plan:
{chr(10).join(plan_lines)}

Family members:
{chr(10).join(member_lines)}

Dietary constraints:
- Forbidden: {pref_result['forbidden_tags'] or 'none'}
- Preferred: {pref_result['allowed_tags'] or 'none'}

CRITICAL RULES — you must follow these exactly:
1. Whenever the user asks to swap, change, replace, or expresses dissatisfaction with a meal, you MUST call the replace_meal tool. No exceptions.
2. NEVER describe, name, or claim a replacement has happened without first calling replace_meal. If you say a meal was replaced, the tool must have been called.
3. NEVER invent recipe names. You only know about the recipes shown above. Do not suggest or describe recipes that are not in the current plan.
4. After the tool returns a result, report exactly what the tool found (the recipe name it returned), nothing else.
5. If the tool result starts with "Failed to replace" — the replacement DID NOT happen. You MUST say "I couldn't find a suitable replacement" and MUST NOT mention any recipe name.

Other guidelines:
- If no specific meal is mentioned but context is clear, infer which one to replace.
- Answer nutrition or ingredient questions based on the plan context above.
- Keep responses concise and friendly."""
