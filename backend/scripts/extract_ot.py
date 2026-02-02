filename = "stellar_app_bundle.js"
start_idx = 850354
length = 20000 

with open(filename, "r", encoding="utf-8") as f:
    f.seek(start_idx)
    content = f.read(length)

with open("ot_component.js", "w", encoding="utf-8") as out:
    out.write(content)

print("Extracted OT component to ot_component.js")
