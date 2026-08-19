"""
PantryChef AI - Streamlit Web Application
=========================================
An AI-powered recipe generation and meal planning application built with Python, Streamlit,
LLM Integration (Qwen2.5-0.5B-Instruct / LLM APIs), and custom prompt engineering.
"""

import streamlit as st
import os
import json
from model import calculate_macros, recommend_meals
from model_backend import get_qwen_response, generate_culinary_fallback

# Page Configuration
st.set_page_config(
    page_title="PantryChef AI - Smart Recipe Generator",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ea580c, #f59e0b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: rgba(241, 245, 249, 0.6);
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
    }
    .metric-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-lbl {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #64748b;
        font-weight: 600;
    }
    .stButton>button {
        background: linear-gradient(135deg, #ea580c, #e11d48);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown('<div class="main-header">🍳 PantryChef AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Transform everyday pantry ingredients into delicious, nutritionally-balanced recipes with AI</div>', unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Chef's Settings")
    
    diet_preference = st.selectbox(
        "🥗 Dietary Preference",
        options=["Omnivore (No Restrictions)", "Vegetarian", "Vegan", "Non-Vegetarian / High-Protein"],
        index=0
    )
    # Map to internal key
    pref_map = {
        "Omnivore (No Restrictions)": "none",
        "Vegetarian": "veg",
        "Vegan": "vegan",
        "Non-Vegetarian / High-Protein": "non-veg"
    }
    pref_key = pref_map[diet_preference]

    cuisine_choice = st.selectbox(
        "🌍 Cuisine Style",
        options=["Chef's Choice (General)", "Italian", "Indian", "Mexican", "Mediterranean", "Asian / Stir-fry", "French Bistro", "American Homestyle"],
        index=0
    )
    cuisine_clean = cuisine_choice.split()[0].lower()

    servings = st.slider("👥 Servings / Portions", min_value=1, max_value=10, value=2)

    st.markdown("---")
    st.subheader("🧠 LLM & Inference Engine")
    engine_choice = st.radio(
        "Generation Backend",
        options=["Local Qwen2.5 LLM / Hybrid", "Fast Culinary Synthesis Engine"],
        index=0
    )

    st.markdown("---")
    st.info("💡 **Tip:** PantryChef AI validates input ingredients against your dietary preference to ensure zero dietary conflicts!")

# Main Layout
col_input, col_output = st.columns([1, 1.25], gap="large")

with col_input:
    st.subheader("🧺 What's in Your Pantry?")
    
    # Quick Add Buttons
    st.caption("⚡ Quick-Add Popular Staples:")
    quick_cols = st.columns(4)
    
    if "ingredient_list" not in st.session_state:
        st.session_state.ingredient_list = ["150g Rice", "2 Tomatoes (count)", "10g Olive Oil"]
        
    def add_staple(item):
        if item not in st.session_state.ingredient_list:
            st.session_state.ingredient_list.append(item)

    with quick_cols[0]:
        if st.button("+ Rice", use_container_width=True): add_staple("150g Rice")
        if st.button("+ Garlic", use_container_width=True): add_staple("3 Garlic (count)")
    with quick_cols[1]:
        if st.button("+ Tomatoes", use_container_width=True): add_staple("2 Tomatoes (count)")
        if st.button("+ Spinach", use_container_width=True): add_staple("100g Spinach")
    with quick_cols[2]:
        if pref_key not in ['veg', 'vegan']:
            if st.button("+ Chicken", use_container_width=True): add_staple("200g Chicken")
        else:
            if st.button("+ Tofu", use_container_width=True): add_staple("150g Tofu")
        if st.button("+ Onion", use_container_width=True): add_staple("1 Onion (count)")
    with quick_cols[3]:
        if pref_key not in ['veg', 'vegan']:
            if st.button("+ Eggs", use_container_width=True): add_staple("2 Eggs (count)")
        else:
            if st.button("+ Beans", use_container_width=True): add_staple("150g Beans")
        if st.button("+ Olive Oil", use_container_width=True): add_staple("15ml Olive Oil")

    # Custom Ingredients Input
    st.markdown("##### 📝 Selected Ingredients (One per line):")
    ingredients_text = st.text_area(
        "Enter or edit your ingredients with optional quantities (e.g., 200g Chicken, 2 Eggs, 100g Spinach):",
        value="\n".join(st.session_state.ingredient_list),
        height=180
    )
    
    # Update session state list
    current_ingredients = [line.strip() for line in ingredients_text.splitlines() if line.strip()]

    # Input Validation logic
    non_veg_items = {'chicken', 'fish', 'eggs', 'egg', 'beef', 'pork', 'salmon', 'tuna', 'meat'}
    dairy_items = {'cheese', 'milk', 'butter', 'yogurt', 'paneer'}
    
    validation_warnings = []
    if pref_key in ['veg', 'vegan']:
        for ing in current_ingredients:
            if any(nv in ing.lower() for nv in non_veg_items):
                validation_warnings.append(f"⚠️ Non-vegetarian ingredient '{ing}' detected while diet preference is '{diet_preference}'.")
    if pref_key == 'vegan':
        for ing in current_ingredients:
            if any(d in ing.lower() for d in dairy_items):
                validation_warnings.append(f"⚠️ Dairy ingredient '{ing}' detected while diet preference is 'Vegan'.")

    for warn in validation_warnings:
        st.warning(warn)

    generate_clicked = st.button("✨ Generate AI Recipe & Macros", use_container_width=True)

    # Prompt Engineering Inspection Expander
    with st.expander("🔍 View System Prompt & Prompt Engineering Logic"):
        st.markdown(f"""
        **System Prompt Architecture:**
        ```text
        <|im_start|>system
        You are PantryChef AI, an expert culinary chef and nutritionist. Create clear, delicious, realistic recipes using the user's available ingredients with step-by-step numbered instructions, preparation notes, cooking times, and chef tips.<|im_end|>
        <|im_start|>user
        Generate a delicious, complete {pref_key} recipe using these available ingredients: {', '.join(current_ingredients)}. Target Cuisine: {cuisine_clean}. Scale recipe for {servings} serving(s). Include a creative Recipe Title, Prep Time, Cook Time, Ingredients Checklist, Step-by-Step Instructions, and Chef's Pro-Tips.<|im_end|>
        <|im_start|>assistant
        ```
        """)

# Right Column: Recipe & Macros Output
with col_output:
    st.subheader("🍽️ Chef's Custom Creation")
    
    if generate_clicked:
        if not current_ingredients:
            st.error("Please add at least one ingredient before generating!")
        else:
            with st.spinner("🧑‍🍳 Chef AI is crafting your recipe and computing nutritional macros..."):
                # 1. Macro and Nutritional Calculation
                macros = calculate_macros(current_ingredients, servings)
                
                # 2. Recipe Generation (Qwen2.5 or Fallback)
                if engine_choice == "Fast Culinary Synthesis Engine":
                    recipe_text = generate_culinary_fallback(current_ingredients, pref_key, cuisine_clean, servings)
                else:
                    prompt = (
                        f"Generate a delicious, complete {pref_key} recipe using these available ingredients: {', '.join(current_ingredients)}. "
                        f"Target Cuisine: {cuisine_clean}. Scale recipe for {servings} serving(s). "
                        f"Include a creative Recipe Title, Prep Time, Cook Time, Ingredients Checklist, Step-by-Step Instructions, and Chef's Pro-Tips."
                    )
                    recipe_text = get_qwen_response(
                        user_input=prompt,
                        ingredients=current_ingredients,
                        preference=pref_key,
                        cuisine=cuisine_clean,
                        servings=servings
                    )
                
                st.session_state.active_recipe = recipe_text
                st.session_state.active_macros = macros

    if "active_recipe" in st.session_state and st.session_state.active_recipe:
        macros = st.session_state.active_macros
        
        # Display Macronutrients Dashboard
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Total Calories</div>
                <div class="metric-val" style="color: #ea580c;">{int(macros['total_calories'])} <span style="font-size:0.8rem;">kcal</span></div>
                <div style="font-size:0.75rem; color:#64748b;">{int(macros['per_serving_calories'])} kcal/srv</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Carbs</div>
                <div class="metric-val" style="color: #3b82f6;">{int(macros['total_carbs'])}g</div>
                <div style="font-size:0.75rem; color:#64748b;">{int(macros['per_serving_carbs'])}g/srv</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Protein</div>
                <div class="metric-val" style="color: #10b981;">{int(macros['total_protein'])}g</div>
                <div style="font-size:0.75rem; color:#64748b;">{int(macros['per_serving_protein'])}g/srv</div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Fats</div>
                <div class="metric-val" style="color: #eab308;">{int(macros['total_fat'])}g</div>
                <div style="font-size:0.75rem; color:#64748b;">{int(macros['per_serving_fat'])}g/srv</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        
        # Render Recipe Markdown
        st.markdown(st.session_state.active_recipe)

        # Download Recipe Button
        st.download_button(
            label="📥 Download Recipe (Markdown)",
            data=st.session_state.active_recipe,
            file_name="pantrychef_recipe.md",
            mime="text/markdown"
        )
    else:
        st.info("👈 Add your pantry ingredients on the left and click **Generate AI Recipe & Macros** to create your customized meal!")
