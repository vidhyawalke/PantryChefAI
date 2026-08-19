import os
import json
import sqlite3
import logging
import re
from datetime import timedelta
from functools import lru_cache

from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

from model_backend import get_qwen_response
from model import calculate_macros, recommend_meals

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("PantryChefAI")

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'pantrychef_secure_vault_key_2026')
app.permanent_session_lifetime = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Non-vegetarian items to filter based on diet preferences
NON_VEG_ITEMS = {
    'chicken', 'fish', 'eggs', 'egg', 'beef', 'pork', 
    'salmon', 'tuna', 'meat', 'bacon', 'turkey', 'prawns', 'shrimp'
}

DAIRY_ITEMS = {
    'cheese', 'cheddar', 'mozzarella', 'milk', 'butter', 
    'yogurt', 'cream', 'paneer', 'ghee'
}

def get_db():
    """Returns a SQLite connection with row factory for cleaner dictionary access."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            password TEXT NOT NULL,
            preference TEXT DEFAULT 'none',
            recipes TEXT DEFAULT '[]'
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_email ON users(email)')
    conn.commit()
    conn.close()

def get_user_by_email(email):
    """Retrieve a user row by email."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    user = c.fetchone()
    conn.close()
    return user

def authenticate_user(email, password):
    """
    Authenticate a user by email and password.
    Supports secure hashed passwords as well as seamless migration from legacy plaintext passwords.
    """
    email_clean = email.strip().lower()
    user = get_user_by_email(email_clean)
    if not user:
        return None
    
    stored_password = user['password']
    
    # Check if stored password is a Werkzeug hash
    is_valid = False
    if stored_password.startswith(('pbkdf2:', 'scrypt:', 'argon2:')):
        is_valid = check_password_hash(stored_password, password)
    else:
        # Legacy plaintext check
        if stored_password == password:
            is_valid = True
            # Upgrade legacy plaintext password to secure hash in the background
            try:
                hashed_pw = generate_password_hash(password)
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_pw, email_clean))
                conn.commit()
                conn.close()
                logger.info(f"Upgraded password hash for legacy user: {email_clean}")
            except Exception as e:
                logger.error(f"Error upgrading legacy password hash: {e}")
                
    return user if is_valid else None

def add_user(email, full_name, password, preference='none'):
    """Create a new user with hashed password."""
    email_clean = email.strip().lower()
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_clean):
        return False, "Invalid email address format."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if not full_name.strip():
        return False, "Full name cannot be empty."
        
    hashed_password = generate_password_hash(password)
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (email, full_name, password, preference, recipes) VALUES (?, ?, ?, ?, ?)",
            (email_clean, full_name.strip(), hashed_password, preference, json.dumps([]))
        )
        conn.commit()
        logger.info(f"New user registered: {email_clean}")
        return True, "Registration successful."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    except Exception as e:
        logger.error(f"Database error during add_user: {e}")
        return False, "An error occurred while creating your account."
    finally:
        conn.close()

def get_user_saved_recipes(email):
    """Retrieve parsed list of saved recipes for a user."""
    user = get_user_by_email(email)
    if not user:
        return []
    raw_recipes = user['recipes']
    if not raw_recipes:
        return []
    try:
        return json.loads(raw_recipes)
    except Exception:
        # Fallback in case legacy data was stored using str(dict)
        try:
            import ast
            return ast.literal_eval(raw_recipes)
        except Exception:
            return []

def save_recipe_for_user(email, recipe_text, ingredients, cuisine="general", servings=1, macros=None):
    """Save a recipe and its nutritional metadata into the user's profile."""
    recipes = get_user_saved_recipes(email)
    
    # Extract title from recipe text
    title = "Chef's Special Recipe"
    for line in recipe_text.splitlines():
        line_clean = line.strip().replace('#', '').strip()
        if line_clean:
            title = line_clean
            break

    new_entry = {
        'id': len(recipes) + 1,
        'title': title,
        'recipe': recipe_text,
        'ingredients': ingredients,
        'cuisine': cuisine,
        'servings': servings,
        'macros': macros or calculate_macros(ingredients, servings)
    }
    recipes.append(new_entry)
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET recipes = ? WHERE email = ?", (json.dumps(recipes), email.strip().lower()))
    conn.commit()
    conn.close()
    return True

def delete_recipe_for_user(email, recipe_index):
    """Delete a saved recipe by index."""
    recipes = get_user_saved_recipes(email)
    if 0 <= recipe_index < len(recipes):
        recipes.pop(recipe_index)
        # Re-index
        for idx, r in enumerate(recipes):
            r['id'] = idx + 1
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET recipes = ? WHERE email = ?", (json.dumps(recipes), email.strip().lower()))
        conn.commit()
        conn.close()
        return True
    return False

def update_preference(email, preference):
    """Update dietary preference."""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET preference = ? WHERE email = ?", (preference, email.strip().lower()))
    conn.commit()
    conn.close()

def get_ingredients_from_form(form, preference='none'):
    """Extract and validate ingredients from the dynamic form submission."""
    ingredients = []
    i = 0
    pref_lower = preference.lower() if preference else 'none'

    # Dynamic row items
    while True:
        item = form.get(f'ingredient_{i}')
        qty = form.get(f'quantity_{i}')
        unit = form.get(f'unit_{i}')
        
        if item is None and i > 25:
            break
        if item and item.strip():
            item_clean = item.strip().lower()
            qty_clean = qty.strip() if qty else '100'
            unit_clean = unit.strip() if unit else 'g'
            
            # Filter non-vegetarian / dairy items if preference restricts it
            if pref_lower in ['veg', 'vegetarian'] and any(non_veg in item_clean for non_veg in NON_VEG_ITEMS):
                i += 1
                continue
            if pref_lower == 'vegan' and (any(non_veg in item_clean for non_veg in NON_VEG_ITEMS) or any(dairy in item_clean for dairy in DAIRY_ITEMS)):
                i += 1
                continue

            try:
                qty_val = float(qty_clean)
            except ValueError:
                qty_val = 100.0

            if unit_clean == 'count':
                ingredients.append(f"{int(qty_val)} {item_clean} (count)")
            else:
                ingredients.append(f"{qty_val:g}{unit_clean} {item_clean}")
        i += 1

    # Checkbox common staples
    common_items = [
        'rice', 'chicken', 'pasta', 'cheese', 'fish', 'tomatoes',
        'potatoes', 'broccoli', 'garlic', 'olive oil', 'eggs', 'spinach', 'onion', 'carrot'
    ]
    for item in common_items:
        if form.get(item):
            if pref_lower in ['veg', 'vegetarian'] and item in NON_VEG_ITEMS:
                continue
            if pref_lower == 'vegan' and (item in NON_VEG_ITEMS or item in DAIRY_ITEMS):
                continue
            ingredients.append(f"100g {item}")

    # Remove duplicates preserving order
    seen = set()
    unique_ingredients = []
    for ing in ingredients:
        if ing not in seen:
            seen.add(ing)
            unique_ingredients.append(ing)

    return unique_ingredients

@lru_cache(maxsize=128)
def suggest_recipe_cached(ingredients_tuple, preference='none', cuisine='general', servings=1):
    """Generate recipe using AI model or culinary synthesis engine."""
    ingredients = list(ingredients_tuple)
    if not ingredients:
        ingredients = ["100g rice", "50g tomatoes", "20g olive oil"]
        
    prompt = (
        f"Generate a delicious, complete {preference} recipe using these available ingredients: {', '.join(ingredients)}. "
        f"Target Cuisine: {cuisine}. Scale recipe for {servings} serving(s). "
        f"Include a creative Recipe Title, Prep Time, Cook Time, Ingredients Checklist, Step-by-Step Instructions, and Chef's Pro-Tips."
    )
    
    recipe_body = get_qwen_response(
        user_input=prompt,
        ingredients=ingredients,
        preference=preference,
        cuisine=cuisine,
        servings=servings
    )
    return recipe_body

# Initialize database schema on startup
init_db()

@app.route('/', methods=['GET', 'POST'])
def home():
    init_db()
    theme = request.cookies.get('theme', 'dark')
    current_user_email = session.get('user')
    user_data = get_user_by_email(current_user_email) if current_user_email else None
    
    if user_data:
        session['full_name'] = user_data['full_name']
        session['preference'] = user_data['preference']
    
    if request.method == 'POST':
        # 1. Login Action
        if 'login_email' in request.form:
            email = request.form.get('login_email', '')
            password = request.form.get('login_password', '')
            user = authenticate_user(email, password)
            if user:
                session.permanent = True
                session['user'] = user['email']
                session['full_name'] = user['full_name']
                session['preference'] = user['preference']
                flash(f"Welcome back, {user['full_name']}! Ready to cook?", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid email or password. Please try again.", "error")
                return render_template('index.html', page='login', theme=theme)

        # 2. Signup Action
        elif 'signup_email' in request.form:
            email = request.form.get('signup_email', '')
            full_name = request.form.get('full_name', '')
            password = request.form.get('signup_password', '')
            preference = request.form.get('preference', 'none')
            
            success, message = add_user(email, full_name, password, preference)
            if success:
                session.permanent = True
                session['user'] = email.strip().lower()
                session['full_name'] = full_name.strip()
                session['preference'] = preference
                flash("Account created successfully! Welcome to PantryChefAI.", "success")
                return redirect(url_for('home'))
            else:
                flash(message, "error")
                return render_template('index.html', page='login', theme=theme)

        # 3. Generate Recipe Action
        elif 'generate_recipe' in request.form:
            if not current_user_email:
                return redirect(url_for('home'))
                
            preference = session.get('preference', 'none')
            ingredients = get_ingredients_from_form(request.form, preference)
            
            if not ingredients:
                flash("Please add or select at least one ingredient to generate a recipe!", "warning")
                return redirect(url_for('home'))
                
            cuisine = request.form.get('cuisine', 'general')
            try:
                servings = max(1, int(request.form.get('servings', 1)))
            except ValueError:
                servings = 1
                
            recipe = suggest_recipe_cached(tuple(ingredients), preference, cuisine, servings)
            macros = calculate_macros(ingredients, servings)
            
            session['recipe'] = recipe
            session['ingredients'] = ingredients
            session['cuisine'] = cuisine
            session['servings'] = servings
            session['macros'] = macros
            
            saved_recipes = get_user_saved_recipes(current_user_email)
            meal_ideas = recommend_meals(preference, macros['per_serving_calories'], cuisine)

            return render_template(
                'index.html',
                page='main',
                recipe=recipe,
                ingredients=ingredients,
                macros=macros,
                cuisine=cuisine,
                servings=servings,
                meal_ideas=meal_ideas,
                saved_recipes=saved_recipes,
                theme=theme,
                full_name=session.get('full_name'),
                preference=preference
            )

        # 4. Save Recipe Action
        elif 'save_recipe' in request.form:
            if current_user_email and session.get('recipe') and session.get('ingredients'):
                recipe_text = session.get('recipe')
                ingredients = session.get('ingredients')
                cuisine = session.get('cuisine', 'general')
                servings = session.get('servings', 1)
                macros = session.get('macros', calculate_macros(ingredients, servings))
                
                save_recipe_for_user(current_user_email, recipe_text, ingredients, cuisine, servings, macros)
                flash("Recipe saved to your pantry collection!", "success")
                
                saved_recipes = get_user_saved_recipes(current_user_email)
                return render_template(
                    'index.html',
                    page='main',
                    recipe=recipe_text,
                    ingredients=ingredients,
                    macros=macros,
                    cuisine=cuisine,
                    servings=servings,
                    saved_recipes=saved_recipes,
                    theme=theme,
                    full_name=session.get('full_name'),
                    preference=session.get('preference', 'none')
                )

        # 5. Switch Theme Action
        elif 'theme' in request.form:
            new_theme = 'dark' if request.form['theme'] == 'dark' else 'light'
            resp = redirect(url_for('home'))
            resp.set_cookie('theme', new_theme, max_age=60*60*24*365)
            return resp

    # GET Request Handling
    if not current_user_email:
        return render_template('index.html', page='login', theme=theme)

    saved_recipes = get_user_saved_recipes(current_user_email)
    meal_ideas = recommend_meals(session.get('preference', 'none'), 450)
    
    return render_template(
        'index.html',
        page='main',
        recipe=session.get('recipe'),
        ingredients=session.get('ingredients', []),
        macros=session.get('macros'),
        cuisine=session.get('cuisine', 'general'),
        servings=session.get('servings', 1),
        meal_ideas=meal_ideas,
        saved_recipes=saved_recipes,
        theme=theme,
        full_name=session.get('full_name'),
        preference=session.get('preference', 'none')
    )

@app.route('/update_preference_route', methods=['POST'])
def update_preference_route():
    if 'user' in session:
        preference = request.form.get('preference', 'none')
        update_preference(session['user'], preference)
        session['preference'] = preference
        flash(f"Dietary preference updated to: {preference.capitalize()}", "info")
    return redirect(url_for('home'))

@app.route('/delete_recipe', methods=['POST'])
def delete_recipe():
    if 'user' in session:
        recipe_idx = int(request.form.get('recipe_index', -1))
        if delete_recipe_for_user(session['user'], recipe_idx):
            flash("Recipe removed from your saved list.", "info")
        else:
            flash("Could not delete recipe.", "error")
    return redirect(url_for('home'))

@app.route('/print_recipe', methods=['GET', 'POST'])
def print_recipe():
    recipe = session.get('recipe', '')
    ingredients = session.get('ingredients', [])
    macros = session.get('macros', {})
    cuisine = session.get('cuisine', 'General')
    servings = session.get('servings', 1)
    
    if not recipe:
        flash("No active recipe to print. Generate one first!", "warning")
        return redirect(url_for('home'))
        
    return render_template(
        'print_recipe.html',
        recipe=recipe,
        ingredients=ingredients,
        macros=macros,
        cuisine=cuisine,
        servings=servings,
        full_name=session.get('full_name', 'Chef')
    )

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)