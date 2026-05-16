from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Optional


# --- Auth ---
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v.encode()) > 72:
            raise ValueError("Password must be 72 characters or fewer")
        return v

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str


# --- Family ---
class DietTagCreate(BaseModel):
    tag: str
    is_forbidden: bool = False

class FamilyMemberCreate(BaseModel):
    name: str
    age: int
    calorie_target: int
    diet_tags: List[DietTagCreate] = []

class FamilyMemberUpdate(BaseModel):
    age: int
    calorie_target: int
    diet_tags: List[DietTagCreate] = []

class FamilyCreate(BaseModel):
    name: str
    members: List[FamilyMemberCreate] = []

class DietTagOut(BaseModel):
    tag: str
    is_forbidden: bool
    model_config = ConfigDict(from_attributes=True)

class FamilyMemberOut(BaseModel):
    id: int
    name: str
    age: int
    calorie_target: int
    diet_tags: List[DietTagOut]
    model_config = ConfigDict(from_attributes=True)

class FamilyOut(BaseModel):
    id: int
    name: str
    members: List[FamilyMemberOut]
    model_config = ConfigDict(from_attributes=True)


# --- Fridge ---
class FridgeItemCreate(BaseModel):
    ingredient: str

class FridgeItemOut(BaseModel):
    id: int
    ingredient: str
    model_config = ConfigDict(from_attributes=True)


# --- Recipes ---
class RecipeIngredientOut(BaseModel):
    name: str
    grams_per_base_portion: float
    model_config = ConfigDict(from_attributes=True)

class RecipeTagOut(BaseModel):
    tag: str
    model_config = ConfigDict(from_attributes=True)

class RecipeOut(BaseModel):
    id: int
    name: str
    meal_type: str
    base_portion_grams: float
    calories_per_100g: float
    protein_per_100g: float = 0.0
    fat_per_100g: float = 0.0
    carbs_per_100g: float = 0.0
    description: Optional[str]
    cooking_instructions: Optional[str]
    source: Optional[str] = "local"
    ingredients: List[RecipeIngredientOut]
    tags: List[RecipeTagOut]
    model_config = ConfigDict(from_attributes=True)


class RatingCreate(BaseModel):
    rating: Optional[int] = None  # 1, -1, or None to remove

    @field_validator("rating")
    @classmethod
    def rating_valid(cls, v):
        if v is not None and v not in (1, -1):
            raise ValueError("Rating must be 1 or -1")
        return v


# --- Meal Plan ---
class GeneratePlanRequest(BaseModel):
    family_id: int
    date: str = "today"

class MealPlanItemOut(BaseModel):
    id: int
    meal_type: str
    recipe: Optional[RecipeOut] = None   # None if recipe was deleted
    model_config = ConfigDict(from_attributes=True)

class MealPlanOut(BaseModel):
    id: int
    family_id: int
    date: str
    approved: bool
    items: List[MealPlanItemOut]
    model_config = ConfigDict(from_attributes=True)

class ReplaceMealRequest(BaseModel):
    meal_plan_id: int
    meal_type: str
    recipe_id: int  # current recipe to replace

class MemberPortions(BaseModel):
    member_name: str
    calorie_target: int
    breakfast_grams: float
    lunch_grams: float
    dinner_grams: float
    total_calories: float
    total_protein: float = 0.0
    total_fat: float = 0.0
    total_carbs: float = 0.0

class MealPlanDetailOut(BaseModel):
    plan: MealPlanOut
    member_portions: List[MemberPortions]

# --- Chat ---
class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []

class ChatResponse(BaseModel):
    response: str
    updated_plan: Optional[MealPlanDetailOut] = None


# --- Shopping ---
class ShoppingItemOut(BaseModel):
    ingredient: str
    grams_needed: float
    model_config = ConfigDict(from_attributes=True)

class ShoppingListOut(BaseModel):
    id: int
    meal_plan_id: int
    items: List[ShoppingItemOut]
    model_config = ConfigDict(from_attributes=True)
