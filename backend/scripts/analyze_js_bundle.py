import re

with open("stellar_app_bundle.js", "r", encoding="utf-8") as f:
    content = f.read()

# Look for API endpoint patterns
patterns = [
    r"/api/[a-zA-Z0-9_\-/]+",
    r"supplier-invoices/[a-zA-Z0-9_\-/]+",
    r"retrieve/[a-zA-Z0-9_\-/]+",
]

found = set()
for p in patterns:
    matches = re.findall(p, content)
    for m in matches:
        found.add(m)

print("Found API Patterns:")
for m in sorted(list(found)):
    print(m)
