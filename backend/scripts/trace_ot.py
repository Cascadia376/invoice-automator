import re

filename = "stellar_app_bundle.js"
with open(filename, "r", encoding="utf-8") as f:
    js = f.read()

target_var = "OT"
print(f"Searching for definition of {target_var}...")

indices = [m.start() for m in re.finditer(f"(var|const|let)?\s*{target_var}\s*=", js)]

for idx in indices:
    print(f"Found assignment at {idx}")
    start = max(0, idx - 100)
    end = min(len(js), idx + 3000) # Get a larger chunk to see methods
    print(f"Context:\n{js[start:end]}\n")
