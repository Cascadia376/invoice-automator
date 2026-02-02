import re

with open("stellar_app_bundle.js", "r", encoding="utf-8") as f:
    content = f.read()

keywords = ["supplier-invoices", "retrieve/id", "api/stock"]

print("--- Context Search ---")
for kw in keywords:
    print(f"\nMatches for '{kw}':")
    matches = [m.start() for m in re.finditer(re.escape(kw), content)]
    for start in matches:
        # Get 100 chars context
        ctx_start = max(0, start - 100)
        ctx_end = min(len(content), start + len(kw) + 100)
        print(f"...{content[ctx_start:ctx_end]}...")
