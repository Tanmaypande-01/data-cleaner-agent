"""Steps 2, 7, 8 and part of 9: find the things that could cost the user data,
ask first, and only then apply the answer."""
import numpy as np
import pandas as pd

from type_detection import EMAIL_PATTERN, is_id_like, is_number_column, is_text_column

KEEP = "Keep as is"
REMOVE_ROWS = "Remove these rows"
REMOVE_COLUMN = "Remove this column"
CAP = "Cap to the normal range"
BLANK = "Blank it and auto-fill"

# columns with these words in the name should never be negative
NON_NEGATIVE_WORDS = {"quantity", "qty", "price", "amount", "sales", "revenue", "cost",
                      "salary", "units", "age", "discount"}
DATE_PAIRS = [("order_date", "ship_date"), ("order_date", "delivery_date"), ("ship_date", "delivery_date")]


def _issue(key, kind, step, title, detail, options, default, rows=None, column=None, extra=None):
    return {"key": key, "kind": kind, "step": step, "title": title, "detail": detail,
            "options": options, "default": default, "rows": rows or [], "column": column,
            "extra": extra or {}}


def find_issues(df):
    issues = []
    total = len(df)

    # step 2 - empty rows and duplicates
    empty_rows = df.index[df.isna().all(axis=1)].tolist()
    if empty_rows:
        issues.append(_issue("empty_rows", "rows", "2. Duplicates",
                             "Completely empty rows", f"{len(empty_rows)} rows have no data at all.",
                             [REMOVE_ROWS, KEEP], REMOVE_ROWS, rows=empty_rows))

    candidates = df.drop(index=empty_rows)
    dup_rows = candidates.index[candidates.duplicated(keep="first")].tolist()
    if dup_rows:
        issues.append(_issue("duplicates", "rows", "2. Duplicates",
                             "Duplicate rows",
                             f"{len(dup_rows)} rows repeat an earlier row exactly (after spelling and spacing were cleaned). "
                             "The first copy is always kept.",
                             [REMOVE_ROWS, KEEP], REMOVE_ROWS, rows=dup_rows))

    # step 9 - columns that carry no information
    for col in df.columns:
        missing = df[col].isna().mean()
        if missing == 1:
            detail, default = "Every value is empty.", REMOVE_COLUMN
        elif missing >= 0.6:
            detail, default = f"{missing:.0%} of the values are empty.", KEEP
        elif total > 1 and missing == 0 and df[col].nunique() == 1:
            detail, default = f"Every row has the same value ({df[col].iloc[0]}).", REMOVE_COLUMN
        else:
            continue
        issues.append(_issue(f"column_{col}", "column", "9. Structure", f"Column '{col}' is not useful",
                             detail, [REMOVE_COLUMN, KEEP], default, column=col))

    # step 7 - outliers (IQR rule)
    for col in df.columns:
        series = df[col]
        if not is_number_column(series) or is_id_like(col, series) or series.notna().sum() < 8:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        spread = q3 - q1
        if spread == 0:
            continue
        low, high = q1 - 1.5 * spread, q3 + 1.5 * spread
        if (series.dropna() % 1 == 0).all():
            low, high = np.ceil(low), np.floor(high)
        flagged = series.index[(series < low) | (series > high)].tolist()
        if flagged:
            values = series.loc[flagged]
            issues.append(_issue(f"outliers_{col}", "outliers", "7. Outliers", f"Unusual values in '{col}'",
                                 f"{len(flagged)} values fall outside {low:g} to {high:g} "
                                 f"(smallest {values.min():g}, largest {values.max():g}). "
                                 "Real extremes should be kept; typing mistakes should be capped or removed.",
                                 [KEEP, CAP, REMOVE_ROWS], KEEP, rows=flagged, column=col,
                                 extra={"low": float(low), "high": float(high)}))

    # step 8 - rule checks
    for col in df.columns:
        series = df[col]
        parts = set(col.split("_"))
        if is_number_column(series) and parts & NON_NEGATIVE_WORDS:
            bad = series.index[series < 0].tolist()
            if "age" in parts:
                bad = sorted(set(bad) | set(series.index[series > 120].tolist()))
            if bad:
                issues.append(_issue(f"invalid_{col}", "invalid", "8. Validation", f"Impossible values in '{col}'",
                                     f"{len(bad)} rows are negative" + (" or above 120" if "age" in parts else "") + ".",
                                     [BLANK, REMOVE_ROWS, KEEP], BLANK, rows=bad, column=col))
        if "mail" in col and is_text_column(series):
            filled = series.dropna().astype(str)
            bad = filled.index[~filled.str.match(EMAIL_PATTERN)].tolist()
            if bad:
                issues.append(_issue(f"invalid_{col}", "invalid", "8. Validation", f"Invalid emails in '{col}'",
                                     f"{len(bad)} values do not look like an email address.",
                                     [BLANK, REMOVE_ROWS, KEEP], BLANK, rows=bad, column=col))

    for first, second in DATE_PAIRS:
        if first in df.columns and second in df.columns \
                and pd.api.types.is_datetime64_any_dtype(df[first]) and pd.api.types.is_datetime64_any_dtype(df[second]):
            bad = df.index[df[second] < df[first]].tolist()
            if bad:
                issues.append(_issue(f"order_{first}_{second}", "invalid", "8. Validation",
                                     f"'{second}' is earlier than '{first}'",
                                     f"{len(bad)} rows have dates in the wrong order. 'Blank' clears the {second}.",
                                     [BLANK, REMOVE_ROWS, KEEP], BLANK, rows=bad, column=second))
    return issues


def apply_decisions(df, issues, decisions, log):
    df = df.copy()
    rows_to_drop, columns_to_drop = set(), []

    for issue in issues:
        choice = decisions.get(issue["key"], issue["default"])
        rows, col, step = issue["rows"], issue["column"], issue["step"]

        if choice == KEEP:
            log.add(step, "Kept (your choice)", issue["title"], len(rows))
        elif choice == REMOVE_COLUMN:
            columns_to_drop.append(col)
            log.add(step, "Removed column (approved)", f"{col}: {issue['detail']}")
        elif choice == REMOVE_ROWS:
            rows_to_drop.update(rows)
            log.add(step, "Removed rows (approved)", issue["title"], len(rows))
        elif choice == CAP:
            df[col] = df[col].clip(issue["extra"]["low"], issue["extra"]["high"])
            log.add(step, "Capped values (approved)", f"{col}: {len(rows)} values pulled into the normal range", len(rows))
        elif choice == BLANK:
            df.loc[rows, col] = pd.NaT if pd.api.types.is_datetime64_any_dtype(df[col]) else np.nan
            log.add(step, "Blanked values (approved)", f"{col}: {len(rows)} values cleared, will be auto-filled", len(rows))

    df = df.drop(index=[i for i in rows_to_drop if i in df.index]).drop(columns=columns_to_drop, errors="ignore")
    return df
