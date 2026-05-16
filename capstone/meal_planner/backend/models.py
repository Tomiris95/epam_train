"""SQLAlchemy ORM models for the meal planner database."""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    families = relationship("Family", back_populates="owner")


class Family(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # nullable=True: legacy families created before auth was added have no owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="families")
    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")
    fridge_items = relationship("FridgeItem", back_populates="family", cascade="all, delete-orphan")
    meal_plans = relationship("MealPlan", back_populates="family", cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    calorie_target = Column(Integer, nullable=False)
    family = relationship("Family", back_populates="members")
    diet_tags = relationship("MemberDietTag", back_populates="member", cascade="all, delete-orphan")


class MemberDietTag(Base):
    __tablename__ = "member_diet_tags"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("family_members.id"), nullable=False)
    tag = Column(String, nullable=False)
    is_forbidden = Column(Boolean, default=False)
    member = relationship("FamilyMember", back_populates="diet_tags")


class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    meal_type = Column(String, nullable=False)  # breakfast/lunch/dinner
    base_portion_grams = Column(Float, nullable=False)
    calories_per_100g = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    cooking_instructions = Column(Text, nullable=True)
    source = Column(String, default="local")    # "local" | "spoonacular"
    protein_per_100g = Column(Float, default=0.0)
    fat_per_100g = Column(Float, default=0.0)
    carbs_per_100g = Column(Float, default=0.0)
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    tags = relationship("RecipeTag", back_populates="recipe", cascade="all, delete-orphan")

    @property
    def calories_per_portion(self):
        return (self.base_portion_grams / 100) * self.calories_per_100g


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    name = Column(String, nullable=False)
    grams_per_base_portion = Column(Float, nullable=False)
    recipe = relationship("Recipe", back_populates="ingredients")


class RecipeTag(Base):
    __tablename__ = "recipe_tags"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    tag = Column(String, nullable=False)
    recipe = relationship("Recipe", back_populates="tags")


class FridgeItem(Base):
    __tablename__ = "fridge_items"
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    ingredient = Column(String, nullable=False)
    family = relationship("Family", back_populates="fridge_items")


class MealPlan(Base):
    __tablename__ = "meal_plans"
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    date = Column(String, nullable=False)
    approved = Column(Boolean, default=False)
    family = relationship("Family", back_populates="meal_plans")
    items = relationship("MealPlanItem", back_populates="meal_plan", cascade="all, delete-orphan")
    shopping_list = relationship("ShoppingList", back_populates="meal_plan", uselist=False, cascade="all, delete-orphan")


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"
    id = Column(Integer, primary_key=True, index=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=False)
    meal_type = Column(String, nullable=False)
    # No ON DELETE CASCADE — orphaned items (deleted recipe) are cleaned up
    # by run_migrations() on startup so the plan stays partially intact.
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    meal_plan = relationship("MealPlan", back_populates="items")
    recipe = relationship("Recipe")


class ShoppingList(Base):
    __tablename__ = "shopping_list"
    id = Column(Integer, primary_key=True, index=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=False)
    meal_plan = relationship("MealPlan", back_populates="shopping_list")
    items = relationship("ShoppingItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingItem(Base):
    __tablename__ = "shopping_items"
    id = Column(Integer, primary_key=True, index=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_list.id"), nullable=False)
    ingredient = Column(String, nullable=False)
    grams_needed = Column(Float, nullable=False)
    shopping_list = relationship("ShoppingList", back_populates="items")


class RecipeRating(Base):
    __tablename__ = "recipe_ratings"
    __table_args__ = (UniqueConstraint("user_id", "recipe_id", name="uq_user_recipe"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    rating = Column(Integer, nullable=False)    # 1 = 👍  |  -1 = 👎


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, nullable=False)          # ISO-8601 UTC
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)         # e.g. "plan_generated"
    family_id = Column(Integer, nullable=True)
    plan_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)               # JSON string
