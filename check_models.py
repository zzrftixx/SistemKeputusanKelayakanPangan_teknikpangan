import google.generativeai as genai
import os
import toml

# Load Key
try:
    with open(".streamlit/secrets.toml", "r") as f:
        config = toml.load(f)
        api_key = config.get("GEMINI_API_KEY")
except:
    api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ No API Key found.")
    exit()

genai.configure(api_key=api_key)

print("🔍 Checking available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
