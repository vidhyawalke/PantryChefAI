"""
PantryChefAI - Nutritional Calculation and Meal Recommendation Engine
"""

# Comprehensive nutritional database per 100g or standard unit
NUTRITION_DATABASE = {
    # Grains & Starches
    'rice': {'cal': 130, 'carb': 28.0, 'prot': 2.7, 'fat': 0.3, 'fiber': 0.4},
    'pasta': {'cal': 131, 'carb': 25.0, 'prot': 5.0, 'fat': 1.1, 'fiber': 1.8},
    'bread': {'cal': 265, 'carb': 49.0, 'prot': 9.0, 'fat': 3.2, 'fiber': 2.7},
    'oats': {'cal': 389, 'carb': 66.0, 'prot': 16.9, 'fat': 6.9, 'fiber': 10.6},
    'quinoa': {'cal': 120, 'carb': 21.3, 'prot': 4.4, 'fat': 1.9, 'fiber': 2.8},
    'potatoes': {'cal': 77, 'carb': 17.0, 'prot': 2.0, 'fat': 0.1, 'fiber': 2.2},
    'potato': {'cal': 77, 'carb': 17.0, 'prot': 2.0, 'fat': 0.1, 'fiber': 2.2},
    'flour': {'cal': 364, 'carb': 76.0, 'prot': 10.0, 'fat': 1.0, 'fiber': 2.7},

    # Proteins
    'chicken': {'cal': 165, 'carb': 0.0, 'prot': 31.0, 'fat': 3.6, 'fiber': 0.0},
    'chicken breast': {'cal': 165, 'carb': 0.0, 'prot': 31.0, 'fat': 3.6, 'fiber': 0.0},
    'fish': {'cal': 206, 'carb': 0.0, 'prot': 22.0, 'fat': 12.0, 'fiber': 0.0},
    'salmon': {'cal': 208, 'carb': 0.0, 'prot': 20.0, 'fat': 13.0, 'fiber': 0.0},
    'tuna': {'cal': 132, 'carb': 0.0, 'prot': 28.0, 'fat': 1.0, 'fiber': 0.0},
    'eggs': {'cal': 155, 'carb': 1.1, 'prot': 13.0, 'fat': 11.0, 'fiber': 0.0},
    'egg': {'cal': 78, 'carb': 0.6, 'prot': 6.3, 'fat': 5.3, 'fiber': 0.0},  # per count
    'beef': {'cal': 250, 'carb': 0.0, 'prot': 26.0, 'fat': 15.0, 'fiber': 0.0},
    'pork': {'cal': 242, 'carb': 0.0, 'prot': 27.0, 'fat': 14.0, 'fiber': 0.0},
    'tofu': {'cal': 76, 'carb': 1.9, 'prot': 8.0, 'fat': 4.8, 'fiber': 0.3},
    'paneer': {'cal': 296, 'carb': 4.5, 'prot': 18.3, 'fat': 22.0, 'fiber': 0.0},
    'lentils': {'cal': 116, 'carb': 20.0, 'prot': 9.0, 'fat': 0.4, 'fiber': 7.9},
    'chickpeas': {'cal': 164, 'carb': 27.4, 'prot': 8.9, 'fat': 2.6, 'fiber': 7.6},
    'beans': {'cal': 127, 'carb': 22.8, 'prot': 8.7, 'fat': 0.5, 'fiber': 6.4},

    # Dairy & Fats
    'cheese': {'cal': 113, 'carb': 1.3, 'prot': 7.0, 'fat': 9.0, 'fiber': 0.0},
    'cheddar': {'cal': 402, 'carb': 1.3, 'prot': 25.0, 'fat': 33.0, 'fiber': 0.0},
    'mozzarella': {'cal': 280, 'carb': 3.1, 'prot': 28.0, 'fat': 17.0, 'fiber': 0.0},
    'milk': {'cal': 42, 'carb': 5.0, 'prot': 3.4, 'fat': 1.0, 'fiber': 0.0},
    'butter': {'cal': 717, 'carb': 0.1, 'prot': 0.9, 'fat': 81.0, 'fiber': 0.0},
    'olive oil': {'cal': 884, 'carb': 0.0, 'prot': 0.0, 'fat': 100.0, 'fiber': 0.0},
    'oil': {'cal': 884, 'carb': 0.0, 'prot': 0.0, 'fat': 100.0, 'fiber': 0.0},
    'yogurt': {'cal': 59, 'carb': 3.6, 'prot': 10.0, 'fat': 0.4, 'fiber': 0.0},

    # Vegetables & Produce
    'tomatoes': {'cal': 18, 'carb': 3.9, 'prot': 0.9, 'fat': 0.2, 'fiber': 1.2},
    'tomato': {'cal': 18, 'carb': 3.9, 'prot': 0.9, 'fat': 0.2, 'fiber': 1.2},
    'onion': {'cal': 40, 'carb': 9.3, 'prot': 1.1, 'fat': 0.1, 'fiber': 1.7},
    'onions': {'cal': 40, 'carb': 9.3, 'prot': 1.1, 'fat': 0.1, 'fiber': 1.7},
    'garlic': {'cal': 149, 'carb': 33.0, 'prot': 6.4, 'fat': 0.5, 'fiber': 2.1},
    'spinach': {'cal': 23, 'carb': 3.6, 'prot': 2.9, 'fat': 0.4, 'fiber': 2.2},
    'carrot': {'cal': 41, 'carb': 9.6, 'prot': 0.9, 'fat': 0.2, 'fiber': 2.8},
    'carrots': {'cal': 41, 'carb': 9.6, 'prot': 0.9, 'fat': 0.2, 'fiber': 2.8},
    'broccoli': {'cal': 34, 'carb': 6.6, 'prot': 2.8, 'fat': 0.4, 'fiber': 2.6},
    'bell pepper': {'cal': 20, 'carb': 4.6, 'prot': 0.9, 'fat': 0.2, 'fiber': 1.7},
    'mushrooms': {'cal': 22, 'carb': 3.3, 'prot': 3.1, 'fat': 0.3, 'fiber': 1.0},
    'cucumber': {'cal': 15, 'carb': 3.6, 'prot': 0.7, 'fat': 0.1, 'fiber': 0.5},
    'zucchini': {'cal': 17, 'carb': 3.1, 'prot': 1.2, 'fat': 0.3, 'fiber': 1.0},
    'avocado': {'cal': 160, 'carb': 8.5, 'prot': 2.0, 'fat': 14.7, 'fiber': 6.7},

    # Fruits
    'apple': {'cal': 52, 'carb': 14.0, 'prot': 0.3, 'fat': 0.2, 'fiber': 2.4},
    'banana': {'cal': 89, 'carb': 23.0, 'prot': 1.1, 'fat': 0.3, 'fiber': 2.6},
    'mango': {'cal': 60, 'carb': 15.0, 'prot': 0.8, 'fat': 0.4, 'fiber': 1.6},
    'blueberry': {'cal': 57, 'carb': 14.0, 'prot': 0.7, 'fat': 0.3, 'fiber': 2.4},
    'lemon': {'cal': 29, 'carb': 9.0, 'prot': 1.1, 'fat': 0.3, 'fiber': 2.8},

    # Spices & Condiments
    'honey': {'cal': 304, 'carb': 82.0, 'prot': 0.3, 'fat': 0.0, 'fiber': 0.2},
    'sugar': {'cal': 387, 'carb': 100.0, 'prot': 0.0, 'fat': 0.0, 'fiber': 0.0},
    'turmeric': {'cal': 312, 'carb': 65.0, 'prot': 7.8, 'fat': 3.2, 'fiber': 21.0},
    'cumin': {'cal': 375, 'carb': 44.0, 'prot': 18.0, 'fat': 22.0, 'fiber': 10.5},
    'coriander': {'cal': 298, 'carb': 55.0, 'prot': 12.0, 'fat': 17.8, 'fiber': 41.9},
    'baking powder': {'cal': 53, 'carb': 28.0, 'prot': 0.0, 'fat': 0.0, 'fiber': 0.0},
    'salt': {'cal': 0, 'carb': 0.0, 'prot': 0.0, 'fat': 0.0, 'fiber': 0.0},
    'pepper': {'cal': 251, 'carb': 64.0, 'prot': 10.0, 'fat': 3.3, 'fiber': 25.0},
    'soy sauce': {'cal': 53, 'carb': 4.9, 'prot': 8.1, 'fat': 0.6, 'fiber': 0.8}
}

def parse_ingredient_line(ing_str):
    """Parse ingredient string like '200g chicken' or '2 eggs (count)' into item name and weight in grams."""
    ing_str = ing_str.strip().lower()
    parts = ing_str.split()
    if not parts:
        return 'unknown', 100.0
    
    qty = 100.0
    if '(count)' in ing_str:
        count_val = 1.0
        try:
            count_val = float(parts[0])
        except ValueError:
            count_val = 1.0
        # Check item name
        clean_name = ' '.join(parts[1:]).replace('(count)', '').strip()
        # Estimate average weight per count (e.g. egg ~ 50g, apple ~ 180g, potato ~ 150g)
        item_unit_weights = {'egg': 50, 'eggs': 50, 'apple': 180, 'banana': 120, 'potato': 150, 'onion': 100, 'carrot': 80, 'tomato': 100}
        avg_weight = item_unit_weights.get(clean_name, 100)
        return clean_name, count_val * avg_weight

    raw_qty = parts[0]
    num_part = ''
    unit_part = ''
    for ch in raw_qty:
        if ch.isdigit() or ch == '.':
            num_part += ch
        else:
            unit_part += ch
    
    try:
        qty_num = float(num_part) if num_part else 100.0
    except ValueError:
        qty_num = 100.0
        
    unit = unit_part.lower() or (parts[1] if len(parts) > 1 and parts[1] in ['g', 'kg', 'ml', 'l', 'cup', 'tbsp', 'tsp'] else 'g')
    
    if unit == 'kg' or unit == 'l':
        weight_g = qty_num * 1000.0
    elif unit == 'cup':
        weight_g = qty_num * 240.0
    elif unit == 'tbsp':
        weight_g = qty_num * 15.0
    elif unit == 'tsp':
        weight_g = qty_num * 5.0
    else:
        weight_g = qty_num

    item_name = ' '.join(parts[1:] if unit_part else parts[2:] if len(parts) > 2 and parts[1] in ['g', 'kg', 'ml', 'l', 'cup', 'tbsp', 'tsp'] else parts[1:]).strip()
    return item_name, weight_g

def find_nutrition(item_name):
    """Find matching nutritional profile for an ingredient with fuzzy/partial matching."""
    item_clean = item_name.strip().lower()
    if item_clean in NUTRITION_DATABASE:
        return NUTRITION_DATABASE[item_clean]
    
    # Check partial key matches
    for key, data in NUTRITION_DATABASE.items():
        if key in item_clean or item_clean in key:
            return data
            
    # Default nutritional estimate for unknown ingredients
    return {'cal': 85, 'carb': 10.0, 'prot': 2.5, 'fat': 2.0, 'fiber': 1.5}

def calculate_macros(ingredients, servings=1):
    """
    Calculate total calories, carbohydrates, protein, fat, and fiber for the ingredients list.
    """
    total_cal = 0.0
    total_carb = 0.0
    total_prot = 0.0
    total_fat = 0.0
    total_fiber = 0.0

    for ing in ingredients:
        item_name, weight_g = parse_ingredient_line(ing)
        nutr = find_nutrition(item_name)
        factor = weight_g / 100.0
        total_cal += nutr.get('cal', 0) * factor
        total_carb += nutr.get('carb', 0) * factor
        total_prot += nutr.get('prot', 0) * factor
        total_fat += nutr.get('fat', 0) * factor
        total_fiber += nutr.get('fiber', 0) * factor

    servings = max(1, servings)
    return {
        'total_calories': round(total_cal, 1),
        'total_carbs': round(total_carb, 1),
        'total_protein': round(total_prot, 1),
        'total_fat': round(total_fat, 1),
        'total_fiber': round(total_fiber, 1),
        'per_serving_calories': round(total_cal / servings, 1),
        'per_serving_carbs': round(total_carb / servings, 1),
        'per_serving_protein': round(total_prot / servings, 1),
        'per_serving_fat': round(total_fat / servings, 1),
        'per_serving_fiber': round(total_fiber / servings, 1),
        'servings': servings
    }

def predict_calories(ingredients, servings=1):
    """Returns predicted total calories for the given ingredients list."""
    macros = calculate_macros(ingredients, servings)
    return macros['total_calories']

def recommend_meals(preference='none', target_calories=500, cuisine='general'):
    """
    Recommend meal concepts based on dietary preference and target calorie window.
    """
    recommendations = {
        'veg': [
            {"name": "Mediterranean Quinoa & Roasted Veggie Bowl", "cal": 420, "time": "25 mins"},
            {"name": "Creamy Garlic Spinach & Paneer Skillet", "cal": 480, "time": "20 mins"},
            {"name": "Zesty Chickpea & Avocado Garden Salad", "cal": 380, "time": "15 mins"}
        ],
        'vegan': [
            {"name": "Crispy Tofu & Steamed Broccoli Stir-Fry", "cal": 390, "time": "20 mins"},
            {"name": "Golden Lentil & Turmeric Vegetable Soup", "cal": 340, "time": "30 mins"},
            {"name": "Hearty Avocado & Black Bean Protein Bowl", "cal": 440, "time": "15 mins"}
        ],
        'non-veg': [
            {"name": "Lemon Herb Grilled Chicken with Broccoli & Rice", "cal": 520, "time": "25 mins"},
            {"name": "Pan-Seared Garlic Salmon with Asparagus", "cal": 490, "time": "20 mins"},
            {"name": "Classic Golden Egg & Vegetable Fried Rice", "cal": 460, "time": "18 mins"}
        ],
        'none': [
            {"name": "Chef's Garden Harvest Medley Skillet", "cal": 450, "time": "20 mins"},
            {"name": "Savory Garlic & Herb Rice Bowl with Sautéed Greens", "cal": 410, "time": "25 mins"},
            {"name": "Protein-Packed Omelette with Fresh Tomatoes & Cheese", "cal": 380, "time": "12 mins"}
        ]
    }
    pref_key = preference.lower() if preference and preference.lower() in recommendations else 'none'
    return recommendations.get(pref_key, recommendations['none'])