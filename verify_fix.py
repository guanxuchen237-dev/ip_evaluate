from openai import OpenAI

# The new key provided by user
API_KEY = "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"
BASE_URL = "https://integrate.api.nvidia.com/v1"

print(f"Testing Key: {API_KEY[:10]}...")

try:
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )

    completion = client.chat.completions.create(
        model="minimaxai/minimax-m2.1",
        messages=[{"role": "user", "content": "Hello, are you working?"}],
        temperature=0.5,
        top_p=0.7,
        max_tokens=50,
        stream=False
    )
    
    print("✅ Success!")
    print("Response:", completion.choices[0].message.content)
except Exception as e:
    print("❌ Failed!")
    print(e)
