import os
import sys
import logging

# Prevent protobuf and TensorFlow import conflicts
os.environ["USE_TF"] = "0"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

logger = logging.getLogger(__name__)

# Global model and tokenizer cache for lazy loading
_tokenizer = None
_model = None
_device = None
_model_load_attempted = False

def get_model_and_tokenizer():
    """Lazily load the Qwen model and tokenizer on demand."""
    global _tokenizer, _model, _device, _model_load_attempted
    
    if _model is not None and _tokenizer is not None:
        return _tokenizer, _model, _device
        
    if _model_load_attempted:
        return None, None, None

    _model_load_attempted = True
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        model_name = "Qwen/Qwen2.5-0.5B-Instruct"
        logger.info(f"Loading tokenizer for {model_name}...")
        _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Loading model {model_name} on {_device}...")
        _model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
        _model.to(_device)
        _model.eval()
        logger.info("Qwen model successfully loaded!")
        return _tokenizer, _model, _device
    except Exception as e:
        logger.warning(f"Could not load HuggingFace Qwen model ({e}). Using smart culinary synthesis fallback.")
        return None, None, None

def generate_culinary_fallback(ingredients, preference="none", cuisine="general", servings=1):
    """
    Intelligent culinary recipe synthesis engine used as a fast, reliable fallback 
    or when running in lightweight CPU/offline environments.
    """
    cleaned_ingredients = []
    main_items = []
    for ing in ingredients:
        cleaned = ing.strip()
        if cleaned:
            cleaned_ingredients.append(cleaned)
            # Extract basic food name
            parts = cleaned.split()
            name = parts[-1] if len(parts) > 1 else cleaned
            main_items.append(name.capitalize())

    main_hero = main_items[0] if main_items else "Pantry Medley"
    secondary_hero = f" with {main_items[1]}" if len(main_items) > 1 else ""
    cuisine_title = cuisine.capitalize() if cuisine and cuisine.lower() != 'general' else "Homestyle"
    
    title = f"{cuisine_title} {main_hero}{secondary_hero} Delight"
    prep_time = f"{10 + len(ingredients) * 2} mins"
    cook_time = f"{15 + len(ingredients) * 3} mins"
    
    # Format ingredients list
    ing_list_str = "\n".join([f"- {ing}" for ing in cleaned_ingredients])
    
    # Step-by-step cooking steps
    steps = [
        f"**Preparation**: Wash, peel, and chop the fresh ingredients ({', '.join(main_items[:4]) if main_items else 'pantry items'}) into uniform, bite-sized pieces for even cooking.",
        f"**Heat & Aromatics**: Warm 1-2 tbsp of cooking oil or butter in a skillet or pot over medium heat. Sauté any aromatic ingredients (garlic, onions, spices) for 2 minutes until fragrant and golden.",
        f"**Main Sauté & Sear**: Add {main_hero} and sear gently for 4-6 minutes until lightly browned and infused with flavors.",
        f"**Simmer & Meld**: Incorporate the remaining ingredients ({', '.join(main_items[1:5]) if len(main_items) > 1 else 'seasonings'}). Cover and let simmer over medium-low heat for {cook_time}, stirring occasionally until tender and aromatic.",
        f"**Season & Garnish**: Taste and adjust salt, pepper, or fresh herbs to perfection. Remove from heat.",
        f"**Plate & Serve**: Portion evenly into {servings} warm serving bowl(s). Garnish with a drizzle of olive oil or fresh herbs."
    ]
    
    steps_str = "\n".join([f"{idx+1}. {step}" for idx, step in enumerate(steps)])
    
    diet_badge = f"Dietary: {preference.capitalize()}" if preference and preference != 'none' else "Dietary: All Diets"

    recipe_text = f"""### {title}
**Cuisine:** {cuisine_title} | **Servings:** {servings} | **Prep Time:** {prep_time} | **Cook Time:** {cook_time} | **{diet_badge}**

#### Required Ingredients:
{ing_list_str}

#### Step-by-Step Cooking Instructions:
{steps_str}

#### Chef's Pro-Tip:
For maximum flavor depth, let the dish rest for 3 minutes before serving so the natural juices redistribute evenly. Pair with a fresh side salad or warm bread!"""
    return recipe_text

def get_qwen_response(user_input, ingredients=None, preference="none", cuisine="general", servings=1):
    """
    Generate an AI culinary response using Qwen2.5-0.5B-Instruct, with automatic fallback
    to the smart culinary synthesis engine if model weights are unavailable.
    """
    tokenizer, model, device = get_model_and_tokenizer()
    
    if tokenizer is not None and model is not None:
        try:
            prompt = f"<|im_start|>system\nYou are PantryChef AI, an expert culinary chef and nutritionist. Create clear, delicious, realistic recipes using the user's available ingredients with step-by-step numbered instructions, preparation notes, cooking times, and chef tips.<|im_end|>\n<|im_start|>user\n{user_input}<|im_end|>\n<|im_start|>assistant\n"
            input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)
            output_ids = model.generate(
                input_ids, 
                max_new_tokens=600, 
                do_sample=True, 
                temperature=0.7,
                top_p=0.9
            )
            response = tokenizer.decode(output_ids[0][input_ids.shape[-1]:], skip_special_tokens=True)
            return response.strip()
        except Exception as e:
            logger.error(f"Error during Qwen model inference: {e}")
            
    # Fallback to smart synthesis engine
    if ingredients is None:
        ingredients = ["Pantry Essentials"]
    return generate_culinary_fallback(ingredients, preference, cuisine, servings)