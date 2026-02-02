import re

filename = "stellar_app_bundle.js"

with open(filename, "r", encoding="utf-8") as f:
    content = f.read()

print(f"File read: {len(content)} bytes")
print(f"Head (first 200 chars): {content[:200]}")

print("\n--- Absolute URLs ---")
urls = set(re.findall(r"https?://[^\s\"']+", content))
for u in urls:
    print(u)

print("\n--- Path-like Strings (starting with /) ---")
# Look for strings starting with / inside quotes, length > 5
paths = set(re.findall(r"['\"](/[a-zA-Z0-9_\-/]{5,})['\"]", content))
for p in sorted(list(paths)):
    if "/js/" not in p and "/css/" not in p and "/img/" not in p: # Filter assets
        print(p)

print("\n--- API Keywords Context ---")
keywords = ["stock-import", "inventorymanagement", "supplier-invoices"]
for kw in keywords:
    if kw in content:
        print(f"Found '{kw}'")
        # Print context
        idx = content.find(kw)
        start = max(0, idx - 50)
        end = min(len(content), idx + 100)
        print(f"Context: ...{content[start:end]}...")
