import openpyxl

file_path = r"c:\Users\Jay\Documents\Github\invoice-automator\design_files\Return Authorization Form Revised September 2022.xlsx"

try:
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    
    print("--- Block 2 Detail (Rows 13-22) ---")
    for row in range(13, 23):
        row_vals = []
        for col in range(1, 8): # A to G
            cell = sheet.cell(row=row, column=col)
            val = cell.value if cell.value else "EMPTY"
            row_vals.append(f"{cell.coordinate}:{val}")
        print(f"Row {row}: {', '.join(row_vals)}")

except Exception as e:
    print(f"Error: {e}")
