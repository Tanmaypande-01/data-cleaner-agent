"""Reading uploaded files and writing the Excel result."""
from io import BytesIO

import pandas as pd


def sheet_names(data, filename):
    if filename.lower().endswith(".csv"):
        return []
    return pd.ExcelFile(BytesIO(data)).sheet_names


def _keep_leading_zeros(guessed, as_text):
    """pandas turns '0123' into 123. Put the text version back for columns where that would happen."""
    for col in guessed.columns:
        values = as_text[col].dropna().astype(str)
        if values.str.match(r"^0\d+$").any():
            guessed[col] = as_text[col]
    return guessed


def read_table(data, filename, sheet=None):
    if filename.lower().endswith(".csv"):
        try:
            guessed = pd.read_csv(BytesIO(data))
            as_text = pd.read_csv(BytesIO(data), dtype=str)
        except UnicodeDecodeError:
            guessed = pd.read_csv(BytesIO(data), encoding="latin-1")
            as_text = pd.read_csv(BytesIO(data), encoding="latin-1", dtype=str)
        return _keep_leading_zeros(guessed, as_text)
    # Excel cells already know whether they are text or numbers, so keep them exactly as stored
    return pd.read_excel(BytesIO(data), sheet_name=sheet or 0, dtype=object).infer_objects()


def build_excel(clean, log_frame, summary):
    """One workbook: the clean data, the change log and a before/after summary."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        clean.to_excel(writer, sheet_name="clean_data", index=False)
        log_frame.to_excel(writer, sheet_name="change_log", index=False)
        summary.to_excel(writer, sheet_name="summary", index=False)
        for sheet in writer.sheets.values():
            sheet.freeze_panes = "A2"
            for column in sheet.columns:
                longest = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column[:200])
                sheet.column_dimensions[column[0].column_letter].width = min(max(longest + 2, 10), 45)
    return buffer.getvalue()
