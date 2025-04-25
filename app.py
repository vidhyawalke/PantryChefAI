from flask import Flask, request, render_template, redirect, url_for, session, flash
import sqlite3
from model_backend import get_qwen_response
from functools import lru_cache
from datetime import timedelta
import logging
import re

try:
    from flask_caching import Cache
    caching_enabled = True
except ImportError:
    caching_enabled = False
    Cache = None

app = Flask(__name__, template_folder='templates')
if caching_enabled:
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.secret_key = 'supersecretkey123'
app.permanent_session_lifetime = timedelta(minutes=30)


logging.basicConfig(level=logging.DEBUG)

# Nutritional data 
nutrition = {
    'rice': {'cal': 130, 'carb': 28}, 'chicken': {'cal': 165, 'prot': 31},
    'pasta': {'cal': 131, 'carb': 25}, 'cheese': {'cal': 113, 'fat': 9},
    'fish': {'cal': 206, 'prot': 25}, 'tomatoes': {'cal': 18, 'vitc': 13},
    'potatoes': {'cal': 77, 'carb': 17}, 'carrot': {'cal': 41, 'vitc': 6},
    'spinach': {'cal': 23, 'iron': 2.7}, 'onion': {'cal': 40, 'vitc': 7},
    'apple': {'cal': 52, 'fiber': 2.4}, 'banana': {'cal': 89, 'potassium': 358},
    'mango': {'cal': 60, 'vitc': 36}, 'turmeric': {'cal': 312, 'curcumin': 3},
    'cumin': {'cal': 375, 'iron': 66}, 'coriander': {'cal': 298, 'vitc': 21},
    'blueberry': {'cal': 57, 'vitc': 9.7}, 'honey': {'cal': 304, 'sugar': 82},
    'baking powder': {'cal': 53, 'carb': 28}, 'broccoli': {'cal': 34, 'vitc': 89},
    'garlic': {'cal': 149, 'vitc': 31}, 'olive oil': {'cal': 884, 'fat': 100},
    'eggs': {'cal': 155, 'prot': 13}
}

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, full_name TEXT, password TEXT, preference TEXT, recipes TEXT)''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_email ON users(email)')
    conn.commit()
    conn.close()

def get_user(email, password):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    conn.close()
    return user

def add_user(email, full_name, password, preference):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return False
        logging.debug(f"Attempting to add user: {email}, {full_name}, {preference}")
        c.execute("INSERT INTO users (email, full_name, password, preference, recipes) VALUES (?, ?, ?, ?, ?)", (email, full_name, password, preference, '[]'))
        conn.commit()
        logging.debug("User added successfully")
        return True
    except sqlite3.IntegrityError as e:
        logging.error(f"IntegrityError: {e} - Email {email} already exists")
        return False
    except Exception as e:
        logging.error(f"Unexpected error adding user: {e}")
        return False
    finally:
        conn.close()

def save_recipe(email, recipe, ingredients):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT recipes FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    if user:
        recipes = eval(user[0]) if user[0] else []
        recipes.append({'recipe': recipe, 'ingredients': ingredients})
        c.execute("UPDATE users SET recipes = ? WHERE email = ?", (str(recipes), email))
        conn.commit()
    conn.close()

def update_preference(email, preference):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE users SET preference = ? WHERE email = ?", (preference, email))
    conn.commit()
    conn.close()

def get_ingredients_from_form(form):
    ingredients = []
    i = 0
    # List of non-vegetarian ingredients
    non_veg_items = ['chicken', 'fish','eggs','beef','pork']
    # Get user preference from session
    preference = session.get('preference', 'none')
    
    while True:
        item = form.get(f'ingredient_{i}')
        qty = form.get(f'quantity_{i}')
        unit = form.get(f'unit_{i}')
        if not item:
            break
        if qty and unit and item.strip():
            # Skip non-vegetarian items if preference is vegetarian or vegan
            if (preference in ['veg', 'vegan']) and item.lower().strip() in non_veg_items:
                continue
            if unit == 'count':
                ingredients.append(f"{int(float(qty))} {item.lower()} (count)")
            else:
                ingredients.append(f"{float(qty)}{unit} {item.lower()}")
        i += 1
    common_items = ['rice', 'chicken', 'pasta', 'cheese', 'fish', 'tomatoes', 'potatoes', 'broccoli', 'garlic', 'olive oil', 'eggs']
    for item in common_items:
        if form.get(item):
            # Skip non-vegetarian common items if preference is vegetarian or vegan
            if (preference in ['veg', 'vegan']) and item in non_veg_items:
                continue
            ingredients.append(f"100g {item}")
    return [ing for ing in ingredients if len(ing.split()) >= 2]

@lru_cache(maxsize=128)
def suggest_recipe(ingredients_tuple, cuisine=None, servings=1):
    ingredients = list(ingredients_tuple)
    if not cuisine:
        cuisine = 'general'
    adjusted_ingredients = []
    for ing in ingredients:
        parts = ing.split()
        if len(parts) < 2:
            continue
        qty = float(parts[0].rstrip('glml')) if parts[0].rstrip('glml').replace('.', '').isdigit() else 100
        unit = next((u for u in ['g', 'kg', 'l', 'ml'] if u in parts[0]), 'g')
        item = ' '.join(parts[1:]).rstrip('(count)')
        if unit in ['kg', 'l'] and qty > 2:
            qty = 0.2
        elif unit == 'g' and qty > 2000:
            qty = 200
        if '(count)' in ing:
            adjusted_ingredients.append(f"{int(qty)} {item} (count)")
        else:
            adjusted_ingredients.append(f"{qty}{unit} {item}")
    ingredients = adjusted_ingredients
    total_cal = sum(nutrition.get(i.split()[1], {'cal': 0})['cal'] * (float(i.split()[0].rstrip('glml')) / 100 if i.split()[1] in nutrition else 0) for i in ingredients) * servings or 0
    total_carb = sum(nutrition.get(i.split()[1], {'cal': 0, 'carb': 0}).get('carb', 0) * (float(i.split()[0].rstrip('glml')) / 100 if i.split()[1] in nutrition else 0) for i in ingredients) * servings or 0
    total_prot = sum(nutrition.get(i.split()[1], {'prot': 0}).get('prot', 0) * (float(i.split()[0].rstrip('glml')) / 100 if i.split()[1] in nutrition else 0) for i in ingredients) * servings or 0

    prompt = f"Generate a complete {session.get('preference', 'none')} recipe using ONLY: {', '.join(ingredients)}. Cuisine: {cuisine}. Scale for {servings} servings. Include Ingredients, Preparation, Cooking, Serving."
    recipe = get_qwen_response(prompt)
    return f"~{int(total_cal)} kcal, {int(total_carb)}g carbs, {int(total_prot)}g protein (for {servings} servings)\n{recipe}"

if caching_enabled:
    @cache.cached(timeout=3600)
    @app.route('/', methods=['GET', 'POST'])
    def home():
        init_db()
        theme = request.cookies.get('theme', 'light')
        if request.method == 'POST':
            if 'login_email' in request.form:
                email = request.form['login_email']
                password = request.form['login_password']
                user = get_user(email, password)
                if user:
                    session['user'] = email
                    session['full_name'] = user[1]
                    session['preference'] = user[3]
                    return redirect(url_for('home'))
                flash('Invalid credentials. Please try again or create an account.', 'error')
                return render_template('index.html', page='login', error='Invalid credentials', theme=theme)
            elif 'signup_email' in request.form:
                email = request.form['signup_email']
                full_name = request.form['full_name']
                password = request.form['signup_password']
                preference = 'none'
                logging.debug(f"Signup attempt: email={email}, full_name={full_name}, password={password}")
                if add_user(email, full_name, password, preference):
                    session['user'] = email
                    session['full_name'] = full_name
                    session['preference'] = preference
                    logging.debug("Signup successful, redirecting to signup_success")
                    return render_template('index.html', page='signup_success', message='Signup successful! Redirecting...', theme=theme)
                flash('Email already exists or an error occurred. Please try a different email.', 'error')
                return render_template('index.html', page='login', error='Email already exists or an error occurred', theme=theme)
            elif 'generate_recipe' in request.form:
                ingredients = get_ingredients_from_form(request.form)
                cuisine = request.form.get('cuisine', 'general')
                servings = int(request.form.get('servings', 1))
                recipe = suggest_recipe(tuple(ingredients), cuisine, servings)
                session['recipe'] = recipe
                session['ingredients'] = ingredients
                return render_template('index.html', page='main', recipe=recipe, ingredients=ingredients, theme=theme, full_name=session.get('full_name'), servings=servings, disable_form=True)
            elif 'theme' in request.form:
                theme = 'dark' if request.form['theme'] == 'dark' else 'light'
                resp = redirect(url_for('home'))
                resp.set_cookie('theme', theme)
                return resp
            elif 'print_recipe' in request.form:
                return redirect(url_for('print_recipe'))
            elif 'save_recipe' in request.form:
                if 'user' in session and session.get('recipe') and session.get('ingredients'):
                    save_recipe(session['user'], session['recipe'], session['ingredients'])
                    return render_template('index.html', page='main', recipe=session['recipe'], ingredients=session['ingredients'], theme=theme, full_name=session.get('full_name'), servings=request.form.get('servings', 1), disable_form=True, message='Recipe saved successfully!')
        if 'user' not in session:
            return render_template('index.html', page='login', theme=theme)
        return render_template('index.html', page='main', theme=theme, full_name=session.get('full_name'))
else:
    @app.route('/', methods=['GET', 'POST'])
    def home():
        init_db()
        theme = request.cookies.get('theme', 'light')
        if request.method == 'POST':
            if 'login_email' in request.form:
                email = request.form['login_email']
                password = request.form['login_password']
                user = get_user(email, password)
                if user:
                    session['user'] = email
                    session['full_name'] = user[1]
                    session['preference'] = user[3]
                    return redirect(url_for('home'))
                flash('Invalid credentials. Please try again or create an account.', 'error')
                return render_template('index.html', page='login', error='Invalid credentials', theme=theme)
            elif 'signup_email' in request.form:
                email = request.form['signup_email']
                full_name = request.form['full_name']
                password = request.form['signup_password']
                preference = 'none'
                logging.debug(f"Signup attempt: email={email}, full_name={full_name}, password={password}")
                if add_user(email, full_name, password, preference):
                    session['user'] = email
                    session['full_name'] = full_name
                    session['preference'] = preference
                    logging.debug("Signup successful, redirecting to signup_success")
                    return render_template('index.html', page='signup_success', message='Signup successful! Redirecting...', theme=theme)
                flash('Email already exists or an error occurred. Please try a different email.', 'error')
                return render_template('index.html', page='login', error='Email already exists or an error occurred', theme=theme)
            elif 'generate_recipe' in request.form:
                ingredients = get_ingredients_from_form(request.form)
                cuisine = request.form.get('cuisine', 'general')
                servings = int(request.form.get('servings', 1))
                recipe = suggest_recipe(tuple(ingredients), cuisine, servings)
                session['recipe'] = recipe
                session['ingredients'] = ingredients
                return render_template('index.html', page='main', recipe=recipe, ingredients=ingredients, theme=theme, full_name=session.get('full_name'), servings=servings, disable_form=True)
            elif 'theme' in request.form:
                theme = 'dark' if request.form['theme'] == 'dark' else 'light'
                resp = redirect(url_for('home'))
                resp.set_cookie('theme', theme)
                return resp
            elif 'print_recipe' in request.form:
                return redirect(url_for('print_recipe'))
            elif 'save_recipe' in request.form:
                if 'user' in session and session.get('recipe') and session.get('ingredients'):
                    save_recipe(session['user'], session['recipe'], session['ingredients'])
                    return render_template('index.html', page='main', recipe=session['recipe'], ingredients=session['ingredients'], theme=theme, full_name=session.get('full_name'), servings=request.form.get('servings', 1), disable_form=True, message='Recipe saved successfully!')
        if 'user' not in session:
            return render_template('index.html', page='login', theme=theme)
        return render_template('index.html', page='main', theme=theme, full_name=session.get('full_name'))

@app.route('/update_preference_route', methods=['POST'])
def update_preference_route():
    if 'user' in session:
        preference = request.form.get('preference', 'none')
        update_preference(session['user'], preference)
        session['preference'] = preference
    return redirect(url_for('home'))

@app.route('/print_recipe', methods=['GET', 'POST'])
def print_recipe():
    recipe = session.get('recipe', '')
    ingredients = session.get('ingredients', [])
    if not recipe or not ingredients:
        return redirect(url_for('home'))
    return render_template('print_recipe.html', recipe=recipe, ingredients=ingredients)

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('full_name', None)
    session.pop('preference', None)
    session.pop('recipe', None)
    session.pop('ingredients', None)
    return render_template('index.html', page='logout')

if __name__ == '__main__':
    app.run(debug=True)