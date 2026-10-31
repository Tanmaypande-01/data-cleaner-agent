"""The safe cleaning steps. Nothing in here deletes rows or columns - that part
lives in issue_finder.py because it needs the user's permission first."""
import difflib
import re

import numpy as np
import pandas as pd

from activity_log import ChangeLog
from type_detection import (
    NULL_WORDS, YES_WORDS, is_id_like, is_number_column, is_text_column,
    looks_boolean, looks_like_date, looks_numeric, name_looks_like_id,
    to_dates, to_number,
)

# a few labels that fuzzy matching cannot guess on its own - add your own here
KNOWN_ALIASES = {
    "ny": "New York", "newyork": "New York",
    "usa": "United States", "us": "United States", "unitedstates": "United States",
    "uk": "United Kingdom", "unitedkingdom": "United Kingdom",
}


# ---------- step 9: column names ----------
def tidy_name(name):
    text = str(name).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", text)          # orderDate -> order_Date
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower()
    return text or "column"


def tidy_column_names(df, log):
    seen, final = {}, []
    for name in df.columns:
        new = tidy_name(name)
        if new in seen:
            seen[new] += 1
            new = f"{new}_{seen[new]}"
        else:
            seen[new] = 0
        final.append(new)
    renamed = sum(1 for a, b in zip(df.columns, final) if a != b)
    df.columns = final
    if renamed:
        log.add("9. Structure", "Renamed columns", f"{renamed} column names made lowercase with underscores")
    return df


# ---------- step 5: whitespace and fake blanks ----------
def clean_text_cells(df, log):
    for col in df.columns:
        if not is_text_column(df[col]):
            continue
        original = df[col].astype("string")
        cleaned = original.str.strip().str.replace(r"\s+", " ", regex=True)
        cleaned = cleaned.mask(cleaned.str.lower().isin(NULL_WORDS))
        changed = int((cleaned.fillna("~") != original.fillna("~")).sum())
        df[col] = cleaned.astype(object).where(cleaned.notna(), np.nan)
        if changed:
            log.add("5. Formats", "Trimmed text", f"{col}: fixed spaces / empty-like values in {changed} cells", changed)
    return df


# ---------- step 4: data types ----------
def fix_data_types(df, log, dayfirst=True):
    for col in df.columns:
        series = df[col]
        if not is_text_column(series):
            continue
        if looks_boolean(series):
            lowered = series.astype("string").str.lower()
            df[col] = lowered.isin(list(YES_WORDS)).where(lowered.notna()).astype("boolean")
            log.add("4. Data types", "Converted to yes/no", f"{col} is now True/False")
        elif looks_numeric(series) and not name_looks_like_id(col):
            numbers = to_number(series)
            if numbers.notna().any() and (numbers.dropna() % 1 == 0).all() and not numbers.isna().any():
                numbers = numbers.astype("int64")
            df[col] = numbers
            log.add("4. Data types", "Converted to number", f"{col}: removed currency symbols / commas")
        elif looks_like_date(series):
            dates = to_dates(series, dayfirst)
            bad = int(dates.isna().sum() - series.isna().sum())
            df[col] = dates
            note = f"{col} -> yyyy-mm-dd"
            if bad > 0:
                note += f" ({bad} values could not be read and were left blank)"
            log.add("4. Data types", "Converted to date", note)
    return df


# ---------- step 5: casing ----------
def smart_title(value):
    if not isinstance(value, str):
        return value
    if len(value) <= 3 and value.isupper():      # keep NY, USA, UK as they are
        return value
    return re.sub(r"(?<=\w)'S\b", "'s", value.title())


def is_category_like(name, series):
    values = series.dropna()
    if values.empty or name_looks_like_id(name):
        return False
    avg_len = values.astype(str).str.len().mean()
    unique = values.nunique()
    return avg_len <= 40 and (unique <= 50 or unique / len(values) <= 0.5)


def standardize_case(df, log):
    for col in df.columns:
        if not is_text_column(df[col]):
            continue
        before = df[col].copy()
        if "mail" in col:
            df[col] = df[col].map(lambda v: v.lower() if isinstance(v, str) else v)
        elif is_category_like(col, df[col]):
            df[col] = df[col].map(smart_title)
        changed = int((df[col].fillna("~") != before.fillna("~")).sum())
        if changed:
            log.add("5. Formats", "Made casing consistent", f"{col}: {changed} cells", changed)
    return df


# ---------- step 6: category labels ----------
def variant_key(label):
    return re.sub(r"[^a-z0-9]", "", str(label).lower())


def merge_category_variants(df, log):
    for col in df.columns:
        series = df[col]
        if not is_text_column(series) or not is_category_like(col, series):
            continue
        counts = series.value_counts()
        if len(counts) < 2:
            continue
        # fuzzy matching only for real categories (few distinct values), never for names
        allow_fuzzy = len(counts) / series.notna().sum() <= 0.5
        heads, mapping = {}, {}
        for label in counts.index:               # most common spelling first
            key = variant_key(label)
            if key in KNOWN_ALIASES:
                heads.setdefault(key, KNOWN_ALIASES[key])
                mapping[label] = heads[key]
                continue
            match = key if key in heads else None
            if match is None and allow_fuzzy and len(key) >= 5:
                close = difflib.get_close_matches(key, [k for k in heads if len(k) >= 5], n=1, cutoff=0.88)
                match = close[0] if close else None
            if match is None:
                heads[key] = label
                match = key
            mapping[label] = heads[match]
        changes = {a: b for a, b in mapping.items() if a != b}
        if changes:
            df[col] = series.map(mapping)
            example = next(iter(changes.items()))
            affected = int(series.isin(list(changes)).sum())
            log.add("6. Categories", "Merged spelling variants",
                    f"{col}: {len(changes)} variants merged, e.g. '{example[0]}' -> '{example[1]}'", affected)
    return df


# ---------- step 9: optional restructuring (user driven) ----------
def split_column(df, column, delimiter, new_names, log):
    parts = df[column].astype("string").str.split(delimiter, n=len(new_names) - 1, expand=True)
    parts = parts.reindex(columns=range(len(new_names)))
    for i, name in enumerate(new_names):
        df[tidy_name(name)] = parts[i].str.strip().astype(object)
    log.add("9. Structure", "Split column", f"{column} split into {', '.join(new_names)} (original kept)")
    return df


def join_columns(df, columns, separator, new_name, log):
    df[tidy_name(new_name)] = df[columns].apply(
        lambda row: separator.join(str(v) for v in row if pd.notna(v)), axis=1)
    log.add("9. Structure", "Merged columns", f"{', '.join(columns)} -> {tidy_name(new_name)}")
    return df


def unpivot_columns(df, id_columns, value_columns, var_name, value_name, log):
    long_table = df.melt(id_vars=id_columns, value_vars=value_columns,
                         var_name=tidy_name(var_name), value_name=tidy_name(value_name))
    log.add("9. Structure", "Unpivoted wide table",
            f"{len(value_columns)} columns turned into rows ({len(df)} -> {len(long_table)} rows)",
            len(long_table))
    return long_table


# ---------- step 3: missing values (runs after the user's decisions) ----------
def fill_missing_values(df, log, method="median"):
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if missing == 0:
            continue
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            log.add("3. Missing values", "Left blank", f"{col}: {missing} dates unknown, not guessed", missing)
        elif pd.api.types.is_bool_dtype(series):
            mode = series.mode(dropna=True)
            if len(mode):
                df[col] = series.fillna(mode.iloc[0])
                log.add("3. Missing values", "Filled with most common", f"{col}: {missing} cells -> {mode.iloc[0]}", missing)
        elif is_number_column(series):
            if series.notna().sum() == 0 or is_id_like(col, series):
                log.add("3. Missing values", "Left blank", f"{col}: looks like an id, not guessed", missing)
                continue
            value = series.median() if method == "median" else series.mean()
            was_whole = (series.dropna() % 1 == 0).all()
            if was_whole:
                value = round(value)
            filled = series.fillna(value)
            if was_whole and (filled % 1 == 0).all():
                filled = filled.astype("int64")
            df[col] = filled
            log.add("3. Missing values", f"Filled with {method}", f"{col}: {missing} cells -> {round(float(value), 2)}", missing)
        else:
            df[col] = series.fillna("Unknown")
            log.add("3. Missing values", "Flagged as Unknown", f"{col}: {missing} cells", missing)
    return df


# ---------- step 11: derived columns ----------
def add_derived_fields(df, log):
    added = []

    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])][:3]
    for col in date_cols:
        stamp = df[col].dt
        new_cols = {
            f"{col}_year": stamp.year.astype("Int64"),
            f"{col}_month": stamp.month.astype("Int64"),
            f"{col}_month_name": stamp.month_name(),
            f"{col}_quarter": stamp.quarter.map(lambda q: f"Q{int(q)}" if pd.notna(q) else np.nan),
        }
        for name, values in new_cols.items():
            if name not in df.columns:
                df[name] = values
                added.append(name)

    if "age" in df.columns and is_number_column(df["age"]) and "age_group" not in df.columns:
        bins = [-1, 17, 25, 35, 45, 60, 200]
        labels = ["Under 18", "18-25", "26-35", "36-45", "46-60", "60+"]
        df["age_group"] = pd.cut(df["age"], bins=bins, labels=labels).astype(object)
        added.append("age_group")

    def first_numeric(options):
        return next((c for c in options if c in df.columns and is_number_column(df[c])), None)

    revenue = first_numeric(["revenue", "sales", "total_sales", "sales_amount", "total_amount"])
    cost = first_numeric(["cost", "total_cost", "cogs"])
    qty = first_numeric(["quantity", "qty", "units"])
    price = first_numeric(["unit_price", "price"])

    if revenue is None and qty and price:
        df["line_total"] = df[qty] * df[price]
        revenue = "line_total"
        added.append("line_total")
    if revenue and cost and "profit" not in df.columns:
        df["profit"] = df[revenue] - df[cost]
        df["profit_margin_pct"] = np.where(df[revenue] != 0, (df["profit"] / df[revenue] * 100).round(2), np.nan)
        added += ["profit", "profit_margin_pct"]

    if added:
        log.add("11. Derived fields", "Added new columns", ", ".join(added))
    return df


# ---------- last touch: neat whole-number columns ----------
def tidy_number_types(df):
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_float_dtype(series) and series.notna().any() and (series.dropna() % 1 == 0).all():
            df[col] = series.astype("Int64") if series.isna().any() else series.astype("int64")
    return df
