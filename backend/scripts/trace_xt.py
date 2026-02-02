import re

filename = "stellar_app_bundle.js"
with open(filename, "r", encoding="utf-8") as f:
    js = f.read()

target_var = "xT"
print(f"Searching for definition of {target_var}...")

# Search for assignment
# var xT = ...
# const xT = ...
# xT = ...

indices = [m.start() for m in re.finditer(f"(var|const|let)?\s*{target_var}\s*=", js)]

for idx in indices:
    print(f"Found assignment at {idx}")
    start = max(0, idx - 50)
    end = min(len(js), idx + 2000) # Get a good chunk
    print(f"Context:\n{js[start:end]}\n")

# Also look for explicit usage if it's a module
# xT might be a module from a `require`
