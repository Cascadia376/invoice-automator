import openpyxl

file_path = r"c:\Users\Jay\Documents\Github\invoice-automator\design_files\Return Authorization Form Revised September 2022.xlsx"

try:
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    
    print(f"Searching for 'SKU' in sheet '{sheet.title}'...")
    found = False
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value == "SKU":
                print(f"Found 'SKU' at {cell.coordinate} (Row {cell.row}, Col {cell.column})")
                found = True
    
    if not found:
        print("Did not find 'SKU'")

except Exception as e:
    print(f"Error: {e}")
