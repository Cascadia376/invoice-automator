import re

filename = "stellar_app_bundle.js"
with open(filename, "r", encoding="utf-8") as f:
    js = f.read()

# 1. Find the route definition
# Look for {path:"/supplier-invoices/:id/:type?",component:XX
route_pattern = r'path:"/supplier-invoices/:id/:type\?",component:([a-zA-Z0-9_]+)'
match = re.search(route_pattern, js)

if match:
    component_var = match.group(1)
    print(f"Found component variable: {component_var}")
    
    # 2. Find where this variable is defined. 
    # Usually: var XX = ... or function XX()... or in a list: ..., XX, ...
    # In webpack minified code, often: var XX=n(1234)
    
    # Simple search for "var component_var=" or "component_var="
    # We search for the assignment
    
    def_pattern = f"var {component_var}="
    def_idx = js.find(def_pattern)
    
    if def_idx == -1:
        # Try simple assignment without var (if defined in a comma list)
        def_pattern = f"{component_var}="
        def_idx = js.find(def_pattern)
        
    if def_idx != -1:
        print(f"Found definition at index {def_idx}")
        start = max(0, def_idx - 50)
        end = min(len(js), def_idx + 500)
        print(f"Definition context: ...{js[start:end]}...")
        
        # If it's a webpack module require: var XX=n("abcd")
        # We extract the module ID.
        mod_match = re.search(r'n\("([a-zA-Z0-9]+)"\)', js[def_idx:def_idx+100])
        if mod_match:
            mod_id = mod_match.group(1)
            print(f"It points to module ID: {mod_id}")
            # Identify the module content is tricky in a single bundle file without a map.
            # But let's look for that module ID key in the bundle map if possible.
            # Usually: "abcd":function(t,e,n){...}
            
            mod_def_pattern = f'"{mod_id}":function'
            mod_idx = js.find(mod_def_pattern)
            if mod_idx != -1:
                 print(f"Found module {mod_id} definition!")
                 mstart = mod_idx
                 mend = min(len(js), mod_idx + 2000) # Get a chunk
                 print(f"Module code: ...{js[mstart:mend]}...")
            else:
                print("Could not find module definition directly.")
    else:
        print("Could not find component definition assignment.")

else:
    print("Could not find route definition pattern.")
