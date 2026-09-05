from io import BytesIO
import zipfile

import pandas as pd

def dataframe_to_excel_bytes(sheets):
    '''
    sheets: dict[str, DataFrame]
    '''
    mem = BytesIO()
    with pd.ExcelWriter(mem, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            safe_name = str(sheet_name)[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    return mem.getvalue()

def files_to_zip_bytes(paths):
    mem = BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for path in paths:
            z.write(path, path.name)
    return mem.getvalue()
