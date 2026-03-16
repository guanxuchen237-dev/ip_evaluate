import google.generativeai as genai
import os

api_key = "AIzaSyAqQ9DOKVg5AEJd7YZV4SyWUG1hENnfGUw"
genai.configure(api_key=api_key, transport='rest')

print("Listing available models...")
try:
    with open("models.txt", "w", encoding="utf-8") as f:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
                f.write(m.name + "\n")
except Exception as e:
    print(f"Error listing models: {e}")
