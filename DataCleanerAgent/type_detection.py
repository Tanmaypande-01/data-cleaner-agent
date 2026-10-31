"""Small helpers that look at a column and guess what it really contains."""
import re
import warnings

import pandas as pd

# text values that really just mean "nothing here"
NULL_WORDS = {"", "na", "n/a", "nan", "null", "none", "nil", "-", "--", "?", "missing"}

YES_WORDS = {"yes", "true"}
NO_WORDS = {"no", "false"}

MONEY_JUNK = re.compile(r"[₹$€£,\s]")
DATE_SHAPES = re.compile(
    r"^(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}"
    r"|\d{1,2}[-/ ][A-Za-z]{3,9}[-/ ,]+\d{2,4}"
    r"|[A-Za-z]{3,9} \d{1,2},? \d{2,4})"
)
EMAIL_PATTERN = r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$"

# column names containing these words are treated as identifiers, not measurements
ID_HINTS = {"id", "zip", "pin", "pincode", "phone", "mobile", "code", "sku", "number", "no"}


def is_number_column(series):
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def is_text_column(series):
    return not (
        pd.api.types.is_numeric_dtype(series)
        or pd.api.types.is_datetime64_any_dtype(series)
        or pd.api.types.is_bool_dtype(series)
    )


def name_looks_like_id(name):
    name = str(name)
    return name.endswith("id") or any(part in ID_HINTS for part in name.split("_"))


def is_id_like(name, series):
    if name_looks_like_id(name):
        return True
    # a running number like 1001, 1002, 1003... is a row id (prices and ages are not that dense)
    if is_number_column(series) and len(series) > 20:
        values = series.dropna()
        if len(values) and (values % 1 == 0).all() and values.is_unique:
            return bool(len(values) / (values.max() - values.min() + 1) >= 0.9)
    return False


def filled_text(series):
    """Non-empty values of a column as stripped strings."""
    values = series.dropna().astype(str).str.strip()
    return values[~values.str.lower().isin(NULL_WORDS)]


def to_number(series):
    cleaned = series.astype("string").str.replace(MONEY_JUNK, "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").astype("float64")


def _parse(series, dayfirst):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=dayfirst)
        except (TypeError, ValueError):
            return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)


def to_dates(series, dayfirst=True):
    # year-first dates (2024-03-05) are unambiguous, so they must ignore the day-first setting
    text = series.astype("string")
    year_first = text.str.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}").fillna(False).astype(bool)
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    if year_first.any():
        result[year_first] = _parse(text[year_first], False)
    if (~year_first).any():
        result[~year_first] = _parse(text[~year_first], dayfirst)
    return result


def looks_numeric(series, threshold=0.8):
    values = filled_text(series)
    if values.empty:
        return False
    if values.str.match(r"^0\d+$").any():   # 007, 0123 -> keep as text
        return False
    return to_number(values).notna().mean() >= threshold


def looks_like_date(series, threshold=0.8):
    values = filled_text(series)
    if values.empty:
        return False
    return values.str.match(DATE_SHAPES).mean() >= threshold


def looks_boolean(series):
    values = filled_text(series).str.lower()
    return (not values.empty) and set(values.unique()) <= (YES_WORDS | NO_WORDS)
