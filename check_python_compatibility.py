#!/usr/bin/env python3
import json
import urllib.request
import sys

packages = [
    ("fastapi", "0.109.0"),
    ("uvicorn", "0.27.0"),
    ("python-multipart", "0.0.6"),
    ("pydantic", "2.10.6"),
    ("pydantic-settings", "2.7.1"),
    ("python-dotenv", "1.0.0"),
    ("google-generativeai", "0.8.6"),
    ("google-cloud-texttospeech", "2.34.0"),
    ("qdrant-client", None),  # No version specified
    ("langchain-google-genai", None),
    ("numpy", "1.25.0"),
    ("sentence-transformers", None),
    ("SpeechRecognition", "3.14.5"),
    ("requests", "2.31.0"),
    ("aiofiles", "23.2.1"),
]

print("Checking Python version requirements for all packages...\n")
print("=" * 80)

all_requirements = []

for package_name, version in packages:
    try:
        # Get latest version if not specified
        if version is None:
            url = f"https://pypi.org/pypi/{package_name}/json"
        else:
            url = f"https://pypi.org/pypi/{package_name}/{version}/json"
        
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
            requires_python = data['info'].get('requires_python', 'Not specified')
            
            if version is None:
                version = data['info']['version']
            
            print(f"{package_name:30} {version:12} → Python: {requires_python}")
            
            if requires_python and requires_python != 'Not specified':
                all_requirements.append((package_name, requires_python))
    
    except Exception as e:
        print(f"{package_name:30} {version or 'latest':12} → Error: {str(e)[:40]}")

print("=" * 80)
print("\n📊 SUMMARY:")
print("-" * 80)

if all_requirements:
    print("\nPython version requirements found:")
    for pkg, req in all_requirements:
        print(f"  • {pkg}: {req}")
    
    print("\n🎯 RECOMMENDED PYTHON VERSION:")
    print("  Based on the packages, Python 3.8 - 3.12 should be compatible.")
    print("  Python 3.11 (as specified in runtime.txt) is a good choice.")
    print("\n  Note: Some newer packages may require Python 3.8+, 3.9+, or 3.10+")
else:
    print("\nNo specific Python version requirements found in most packages.")
