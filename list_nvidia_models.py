from openai import OpenAI
import os

# Use the key provided by user
api_key = "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"

client = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key=api_key
)

print(f"Checking models with key: {api_key[:10]}...")

try:
    with open("models.txt", "w", encoding="utf-8") as f:
        models = client.models.list()
        f.write("Available Models:\n")
        
        for m in models:
            mid = m.id
            if 'minimax' in mid.lower() or 'glm' in mid.lower():
                f.write(f"{mid}\n")
    print("Models written to models.txt")
except Exception as e:
    print(f"Error listing models: {e}")
