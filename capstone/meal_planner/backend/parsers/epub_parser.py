"""
EPUB Parser for extracting recipes from "Стол № 5" cookbook
"""
import zipfile
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup


class EPUBRecipeParser:
    """Parses EPUB files to extract recipe data"""
    
    def __init__(self, epub_path: str):
        """Initialize parser with EPUB file path"""
        self.epub_path = Path(epub_path)
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")
    
    def parse(self) -> List[Dict]:
        """Parse EPUB and extract all recipes"""
        recipes = []
        
        with zipfile.ZipFile(self.epub_path, 'r') as epub:
            # Get all XHTML files
            xhtml_files = sorted([f for f in epub.namelist() if f.endswith('.xhtml')])
            
            for xhtml_file in xhtml_files:
                content = epub.read(xhtml_file).decode('utf-8')
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract recipes from this chapter
                chapter_recipes = self._extract_recipes_from_html(soup)
                recipes.extend(chapter_recipes)
        
        return recipes
    
    def _extract_recipes_from_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract recipes from a single HTML chapter"""
        recipes = []
        
        # Find all recipe blocks - they start with subtitle containing recipe name
        body = soup.find('body')
        if not body:
            return recipes
        
        current_section = None  # To track current dish type (breakfast/lunch/dinner)
        
        for element in body.find_all(['div', 'p', 'span']):
            # Check for section headers (meal types, dish categories)
            if element.name == 'div' and 'title' in element.get('class', []):
                section_text = element.get_text(strip=True).lower()
                current_section = self._determine_meal_type(section_text)
            
            # Look for recipe title (strong tag inside p with class subtitle)
            if element.name == 'p' and 'subtitle' in element.get('class', []):
                strong = element.find('strong')
                if strong:
                    recipe_name = strong.get_text(strip=True)
                    
                    # Extract recipe starting from this point
                    recipe = self._extract_recipe_data(element, recipe_name, current_section)
                    if recipe:
                        recipes.append(recipe)
        
        return recipes
    
    def _extract_recipe_data(self, start_element, recipe_name: str, meal_type: Optional[str]) -> Optional[Dict]:
        """Extract complete recipe data starting from recipe title element"""
        
        # Collect all text following the recipe title until we hit another recipe or section
        recipe_text_parts = []
        ingredients_parts = []
        nutrition_data = {}
        cooking_steps = []
        
        current = start_element.next_sibling
        in_ingredients = False
        in_nutrition = False
        in_cooking = False
        
        while current:
            if hasattr(current, 'name'):
                # Stop if we hit another subtitle (new recipe) or title (new section)
                if current.name == 'p':
                    classes = current.get('class', [])
                    if 'subtitle' in classes or 'title' in classes:
                        break
                
                text = current.get_text(strip=True)
                
                # Detect section markers
                if 'Ингредиенты' in text:
                    in_ingredients = True
                    in_nutrition = False
                    in_cooking = False
                elif 'В 100 г блюда:' in text or 'Ккал' in text:
                    in_ingredients = False
                    in_nutrition = True
                    in_cooking = False
                    # Parse this trigger line too — Ккал value lives here
                    nutrition_data = self._parse_nutrition(nutrition_data, text)
                elif 'Приготовление' in text:
                    in_ingredients = False
                    in_nutrition = False
                    in_cooking = True
                elif in_ingredients and current.name == 'p' and text:
                    # Parse ingredient lines (format: "Name – 123 g")
                    if '–' in text:
                        ingredients_parts.append(text)
                elif in_nutrition and current.name == 'p' and text:
                    nutrition_data = self._parse_nutrition(nutrition_data, text)
                elif current.name == 'p' and text:
                    # Try nutrition parsing on any line regardless of section —
                    # the EPUB sometimes lists Белки/Жиры/Углеводы before the Ккал trigger
                    nutrition_data = self._parse_nutrition(nutrition_data, text)
                elif in_cooking and current.name == 'p' and text and text[0].isdigit():
                    # Parse cooking steps
                    cooking_steps.append(text)
                
                recipe_text_parts.append(text)
            
            current = current.next_sibling
        
        # Post-processing: scan the full collected recipe text for nutrition values.
        # This is more reliable than section-tracking because the EPUB places
        # Белки/Жиры/Углеводы lines inside or immediately after the ingredient block,
        # before the Ккал trigger fires.
        # Pattern requires the keyword to be directly followed by a separator
        # (no extra words), which distinguishes "Белки – 5,2" (nutrition) from
        # "Белки яичные – 50" (ingredient: extra word "яичные" between keyword and dash).
        full_text = ' '.join(recipe_text_parts)
        _NUTRITION_RE = [
            (r'Белки\s*[–—:]\s*(\d+[,\.]\d+)',          'proteins'),
            (r'Жиры\s*[–—:]\s*(\d+[,\.]\d+)',            'fats'),
            (r'Углеводы\s*[–—:]\s*(\d+[,\.]\d+)',        'carbs'),
            (r'Ккал\s*[–—:]\s*(\d+(?:[,\.]\d+)?)',       'kcal'),
        ]
        for pattern, key in _NUTRITION_RE:
            m = re.search(pattern, full_text)
            if m:
                nutrition_data[key] = float(m.group(1).replace(',', '.'))

        # Parse ingredients
        ingredients = self._parse_ingredients(ingredients_parts)
        if not ingredients:
            return None

        # Get portion, calories, and macros
        base_portion_grams, calories_per_100g = self._extract_portion_calories(ingredients_parts, nutrition_data)
        
        # Determine meal type if not already set
        if not meal_type:
            meal_type = self._guess_meal_type(recipe_name, ingredients)
        
        # Build cooking instructions
        cooking_instructions = self._build_cooking_instructions(cooking_steps)
        
        # Calculate description from initial text
        description = ' '.join(recipe_text_parts[:3]) if recipe_text_parts else None
        
        tags = ['stol5']
        if self._is_soup_or_salad(recipe_name, recipe_text_parts):
            tags.extend(['lunch', 'dinner'])
        
        recipe = {
            'name': recipe_name,
            'meal_type': meal_type or 'lunch',
            'base_portion_grams': base_portion_grams,
            'calories_per_100g': calories_per_100g,
            'protein_per_100g': nutrition_data.get('proteins', 0.0),
            'fat_per_100g': nutrition_data.get('fats', 0.0),
            'carbs_per_100g': nutrition_data.get('carbs', 0.0),
            'description': description,
            'cooking_instructions': cooking_instructions,
            'ingredients': ingredients,
            'tags': tags,
        }
        
        return recipe
    
    def _parse_ingredients(self, ingredient_lines: List[str]) -> List[Dict]:
        """Parse ingredient lines into ingredient objects"""
        ingredients = []
        
        for line in ingredient_lines:
            # Format: "Name – 123 g" or "Name – 123 мл" or just "Name"
            match = re.match(r'^(.+?)\s*–\s*(\d+(?:,\d+)?)\s*(g|г|мл|ml)?', line)
            if match:
                name = match.group(1).strip()
                amount = float(match.group(2).replace(',', '.'))
                
                ingredients.append({
                    'name': name,
                    'grams_per_base_portion': amount
                })
        
        return ingredients
    
    def _parse_nutrition(self, current_data: Dict, text: str) -> Dict:
        """Parse nutrition information line"""
        # Format: "Белки – 12,3 г" or "Ккал – 90,06"
        if 'Белки' in text and '–' in text:
            match = re.search(r'–\s*([\d,]+)', text)
            if match:
                current_data['proteins'] = float(match.group(1).replace(',', '.'))
        elif 'Жиры' in text and '–' in text:
            match = re.search(r'–\s*([\d,]+)', text)
            if match:
                current_data['fats'] = float(match.group(1).replace(',', '.'))
        elif 'Углеводы' in text and '–' in text:
            match = re.search(r'–\s*([\d,]+)', text)
            if match:
                current_data['carbs'] = float(match.group(1).replace(',', '.'))
        elif 'Ккал' in text and '–' in text:
            match = re.search(r'–\s*([\d,]+)', text)
            if match:
                current_data['kcal'] = float(match.group(1).replace(',', '.'))
        
        return current_data
    
    def _extract_portion_calories(self, ingredient_lines: List[str], nutrition_data: Dict) -> Tuple[float, float]:
        """Extract base portion grams and calories per 100g"""
        # Default values
        base_portion = 300.0
        calories_per_100g = 150.0
        
        # Sum ingredient quantities for base portion
        if ingredient_lines:
            total = 0
            for line in ingredient_lines:
                match = re.search(r'–\s*(\d+(?:,\d+)?)', line)
                if match:
                    total += float(match.group(1).replace(',', '.'))
            
            if total > 0:
                base_portion = total
        
        # Get calories from nutrition data
        if 'kcal' in nutrition_data:
            calories_per_100g = nutrition_data['kcal']
        
        return base_portion, calories_per_100g
    
    def _determine_meal_type(self, section_text: str) -> Optional[str]:
        """Determine meal type from section header"""
        section_lower = section_text.lower()
        
        if any(word in section_lower for word in ['завтрак', 'breakfast', 'омлет', 'каша', 'блины']):
            return 'breakfast'
        elif any(word in section_lower for word in ['суп', 'soup']):
            return 'lunch'
        elif any(word in section_lower for word in ['обед', 'lunch', 'основное', 'мясо', 'рыба', 'птица']):
            return 'lunch'
        elif any(word in section_lower for word in ['ужин', 'dinner', 'закуск', 'салат']):
            return 'dinner'
        
        return None
    
    def _guess_meal_type(self, recipe_name: str, ingredients: List[Dict]) -> str:
        """Guess meal type from recipe name and ingredients"""
        name_lower = recipe_name.lower()
        
        # Breakfast indicators
        if any(word in name_lower for word in ['каша', 'омлет', 'блины', 'запеканка', 'йогурт']):
            return 'breakfast'
        
        # Lunch indicators (soups, mains)
        if any(word in name_lower for word in ['суп', 'борщ', 'щи', 'салат']):
            return 'lunch'
        
        # Dinner indicators (lighter meals)
        if any(word in name_lower for word in ['закуск', 'пюре']):
            return 'dinner'
        
        # Default to lunch for main dishes
        return 'lunch'
    
    def _is_soup_or_salad(self, recipe_name: str, recipe_text_parts: List[str]) -> bool:
        """Detect soups and salads for dual lunch/dinner tagging"""
        text = recipe_name.lower() + ' ' + ' '.join(recipe_text_parts).lower()
        return any(term in text for term in ['суп', 'борщ', 'щи', 'салат'])
    
    def _build_cooking_instructions(self, steps: List[str]) -> str:
        """Build cooking instructions from numbered steps"""
        if not steps:
            return ""
        
        # Steps already have numbers, just join them
        return '\n'.join(steps)
