import yaml

def test_template_validation(template_content, vendor_name="Test Vendor"):
    print(f"Testing template:\n{template_content}")
    
    # Basic YAML syntax fix-up: Ensure keywords exist if LLM forgot
    if "keywords:" not in template_content:
        template_content = f"keywords:\n  - \"{vendor_name}\"\n" + template_content
        print("Fixed-up missing keywords header")
        
    try:
        # Validate YAML
        parsed_yaml = yaml.safe_load(template_content)
        if not isinstance(parsed_yaml, dict) or "issuer" not in parsed_yaml:
            raise ValueError("Template missing 'issuer' or invalid structure")
        
        # If keywords is missing but loaded as dict, add it
        if "keywords" not in parsed_yaml or not parsed_yaml["keywords"]:
            parsed_yaml["keywords"] = [vendor_name]
            template_content = yaml.dump(parsed_yaml, sort_keys=False)
            print("Added missing keywords to dict and re-dumped")

        print("✅ Validation successful")
        print(f"Final template:\n{template_content}")
        return True
    except Exception as yaml_err:
        print(f"❌ Validation failed: {yaml_err}")
        return False

# Test 1: Valid template
print("\n--- Test 1: Valid ---")
test_template_validation("""
issuer: "Test Vendor"
keywords:
  - "Test"
fields:
  amount: "Total\\\\s+(\\\\d+)"
""")

# Test 2: Missing keywords (should be fixed)
print("\n--- Test 2: Missing Keywords ---")
test_template_validation("""
issuer: "No Keywords Vendor"
fields:
  amount: "Total\\\\s+(\\\\d+)"
""", "No Keywords Vendor")

# Test 3: Invalid YAML (mapping error)
print("\n--- Test 3: Invalid YAML ---")
test_template_validation("""
issuer: "Broken Vendor"
fields:
  amount: Total: ([0-9.]+)  # Unquoted colon in value
""")
