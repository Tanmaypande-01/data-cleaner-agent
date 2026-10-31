"""Step 1 - look at the data before touching it, and score how healthy it is."""
import pandas as pd

from type_detection import (
    NULL_WORDS, is_number_column, is_text_column,
    looks_boolean, looks_like_date, looks_numeric,
)


def hidden_blanks(series):
    """Cells like 'N/A' or '-' that are not NaN but still mean 'empty'."""
    if not is_text_column(series):
        return 0
    text = series.dropna().astype(str).str.strip().str.lower()
    return int(text.isin(NULL_WORDS).sum())


def basic_facts(df):
    cells = max(df.shape[0] * df.shape[1], 1)
    missing = int(df.isna().sum().sum()) + sum(hidden_blanks(df[c]) for c in df.columns)
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "missing_cells": missing,
        "missing_pct": round(missing / cells * 100, 1),
        "duplicate_rows": int(df.duplicated().sum()),
    }


def column_report(df):
    rows = []
    for col in df.columns:
        missing = int(df[col].isna().sum()) + hidden_blanks(df[col])
        non_null = df[col].dropna()
        rows.append({
            "column": col,
            "type": str(df[col].dtype),
            "missing": missing,
            "missing_%": round(missing / max(len(df), 1) * 100, 1),
            "unique": int(df[col].nunique()),
            "example": str(non_null.iloc[0]) if len(non_null) else "",
        })
    return pd.DataFrame(rows)


def numeric_summary(df):
    numbers = [c for c in df.columns if is_number_column(df[c])]
    if not numbers:
        return pd.DataFrame()
    return df[numbers].describe().T.round(2)


def _type_health(df):
    text_cols = [c for c in df.columns if is_text_column(df[c])]
    if not text_cols:
        return 1.0
    hiding = sum(
        1 for c in text_cols
        if looks_numeric(df[c]) or looks_like_date(df[c]) or looks_boolean(df[c])
    )
    return 1 - hiding / len(text_cols)


def quality_score(df):
    """0-100 score: 50% completeness, 30% no duplicates, 20% columns stored as the right type."""
    facts = basic_facts(df)
    cells = max(df.shape[0] * df.shape[1], 1)
    completeness = 1 - facts["missing_cells"] / cells
    uniqueness = 1 - facts["duplicate_rows"] / max(len(df), 1)
    types = _type_health(df)
    total = 100 * (0.5 * completeness + 0.3 * uniqueness + 0.2 * types)
    return {
        "score": round(total, 1),
        "Completeness": round(completeness * 100, 1),
        "No duplicates": round(uniqueness * 100, 1),
        "Correct types": round(types * 100, 1),
    }


def compare_totals(before, after):
    """Step 10/12 sanity check: do column totals still add up after cleaning?"""
    rows = []
    for col in before.columns:
        if col in after.columns and is_number_column(before[col]) and is_number_column(after[col]):
            b, a = float(before[col].sum()), float(after[col].sum())
            change = (a - b) / b * 100 if b else 0.0
            rows.append({"column": col, "total_before": round(b, 2),
                         "total_after": round(a, 2), "change_%": round(change, 2)})
    return pd.DataFrame(rows)
