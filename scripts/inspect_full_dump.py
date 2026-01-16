import openpyxl

file_path = r"c:\Users\Jay\Documents\Github\invoice-automator\design_files\Return Authorization Form Revised September 2022.xlsx"

try:
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    print(f"Sheet: {sheet.title}")
    
    for i, row in enumerate(sheet.iter_rows(values_only=True), 1):
        # Convert None to "" for readability
        row_data = [str(x) if x is not None else "" for x in row]
        print(f"Row {i}: {row_data}")
        if i >= 40:
            break
            
except Exception as e:
    print(f"Error: {e}")
