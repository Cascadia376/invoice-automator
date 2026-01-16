import openpyxl

file_path = r"c:\Users\Jay\Documents\Github\invoice-automator\design_files\Return Authorization Form Revised September 2022.xlsx"

try:
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    
    keywords = ["Store Name", "Date:", "Address:", "SKU", "Reason For Return"]
    
    for row in sheet.iter_rows():
        for cell in row:
            val = str(cell.value) if cell.value else ""
            for k in keywords:
                if k in val:
                    print(f"Found '{k}' at {cell.coordinate}: '{val}'")

except Exception as e:
    print(f"Error: {e}")
