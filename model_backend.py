from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer
import torch

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", trust_remote_code=True)

# Load model with manual device management
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", trust_remote_code=True)
model.to(device)
model.eval()

def get_qwen_response(user_input):
    prompt = f"<|user|>\n{user_input}\n<|assistant|>\n"
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)
    output_ids = model.generate(input_ids, max_new_tokens=512, do_sample=True)
    response = tokenizer.decode(output_ids[0][input_ids.shape[-1]:], skip_special_tokens=True)
    return response.strip()