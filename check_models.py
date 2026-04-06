#!/usr/bin/env python3
"""Check available Gemini models"""
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

# Configure API
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=api_key)

print("🔍 Available Gemini Models:\n")
print("-" * 80)

try:
    models = genai.list_models()
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"✅ {model.name}")
            print(f"   Display Name: {model.display_name}")
            print(f"   Description: {model.description[:100] if model.description else 'N/A'}...")
            print()
except Exception as e:
    print(f"❌ Error listing models: {e}")
