"""
Seed database with recipes from EPUB book.
Run: python -m backend.seed_from_epub
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from backend.database import engine, SessionLocal
from backend import models
from backend.parsers.epub_parser import EPUBRecipeParser


def seed_recipes_from_epub(epub_path: str):
    """Parse EPUB and add recipes to database"""
    
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    
    # Parse EPUB
    print(f"Parsing EPUB: {epub_path}")
    parser = EPUBRecipeParser(epub_path)
    recipes_data = parser.parse()
    
    print(f"Found {len(recipes_data)} recipes")
    
    if not recipes_data:
        print("No recipes found in EPUB")
        return
    
    # Add to database
    db = SessionLocal()
    try:
        added_count = 0
        skipped_count = 0
        
        for recipe_data in recipes_data:
            # Check if recipe already exists
            existing = db.query(models.Recipe).filter(
                models.Recipe.name == recipe_data['name']
            ).first()

            if existing:
                # Update nutrition fields for existing recipes
                existing.protein_per_100g  = recipe_data.get('protein_per_100g', 0.0)
                existing.fat_per_100g      = recipe_data.get('fat_per_100g', 0.0)
                existing.carbs_per_100g    = recipe_data.get('carbs_per_100g', 0.0)
                existing.calories_per_100g = recipe_data.get('calories_per_100g', existing.calories_per_100g)
                existing.source            = 'local'
                skipped_count += 1
                print(f"  ↺ Updated '{recipe_data['name']}' "
                      f"(kcal={existing.calories_per_100g}, "
                      f"P={existing.protein_per_100g}, "
                      f"F={existing.fat_per_100g}, "
                      f"C={existing.carbs_per_100g})")
                continue

            # Create recipe
            recipe = models.Recipe(
                name=recipe_data['name'],
                meal_type=recipe_data['meal_type'],
                base_portion_grams=recipe_data['base_portion_grams'],
                calories_per_100g=recipe_data['calories_per_100g'],
                protein_per_100g=recipe_data.get('protein_per_100g', 0.0),
                fat_per_100g=recipe_data.get('fat_per_100g', 0.0),
                carbs_per_100g=recipe_data.get('carbs_per_100g', 0.0),
                description=recipe_data.get('description'),
                cooking_instructions=recipe_data.get('cooking_instructions')
            )
            
            # Add ingredients
            for ingredient_data in recipe_data.get('ingredients', []):
                ingredient = models.RecipeIngredient(
                    name=ingredient_data['name'],
                    grams_per_base_portion=ingredient_data['grams_per_base_portion']
                )
                recipe.ingredients.append(ingredient)
            
            # Add tags
            for tag_name in recipe_data.get('tags', []):
                tag = models.RecipeTag(tag=tag_name)
                recipe.tags.append(tag)
            
            db.add(recipe)
            added_count += 1
            print(f"  ✓ Added '{recipe_data['name']}' ({recipe_data['meal_type']})")
        
        db.commit()
        print(f"\n✓ Successfully added {added_count} recipes ({skipped_count} skipped)")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error adding recipes: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    # Find EPUB file
    epub_path = Path(__file__).parent / 'data' / 'Kollektiv-avtorov_Stol-5-Menyu-dlya-zdorovya-s-rekomendaciyami-specialista.810945.fb2.epub'
    
    if len(sys.argv) > 1:
        epub_path = sys.argv[1]
    
    seed_recipes_from_epub(str(epub_path))
