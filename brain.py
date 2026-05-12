```python
import os
import google.generativeai as genai

# API Key setup
api_key = os.getenv("AIzaSyBWQu_Fu0cbpP9KDppnXwAIt-1n5ydtbkw")
genai.configure(api_key=api_key)

# Auto-detect working model
try:
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model_name = models[0]
except Exception as e:
    print(f"Anchal: Error ho gaya baby - {e}")
    exit()

model = genai.GenerativeModel(model_name=model_name)
chat = model.start_chat(history=[])

print(f"✨ ANCHAL CONNECTED (Model: {model_name}) ✨")

while True:
    user_input = input("Rishabh: ")
    if user_input.lower() in ['exit', 'quit']: break
    response = chat.send_message(user_input)
    print(f"Anchal: {response.text}")
```
