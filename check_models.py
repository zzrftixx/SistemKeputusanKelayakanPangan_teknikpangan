import google.generativeai as genai

api_key = "AIzaSyAsxUN8radcvflnv4_2QsZKrEk69u1FZdA"
genai.configure(api_key=api_key)

print("Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
