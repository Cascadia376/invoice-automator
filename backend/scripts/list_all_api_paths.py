import re

with open("stellar_app_bundle.js", "r", encoding="utf-8") as f:
    content = f.read()

print("--- API Path Search ---")
# Regex for /api/ followed by valid URL chars
matches = set(re.findall(r"/api/[a-zA-Z0-9_\-/]+", content))

for m in sorted(list(matches)):
    print(m)
