"""Step 10 - join a second table onto the main one and check nothing went wrong."""
import pandas as pd

from type_detection import is_number_column


def merge_tables(left, right, left_key, right_key, how, keep_first, log):
    for name, table, key in (("main", left, left_key), ("second", right, right_key)):
        if key not in table.columns:
            raise ValueError(f"Join column '{key}' was not found in the {name} table.")

    left, right = left.copy(), right.copy()
    rows_left = len(left)

    # build a comparable join key (text keys are compared trimmed and lowercase)
    if is_number_column(left[left_key]) and is_number_column(right[right_key]):
        left["_join_key"], right["_join_key"] = left[left_key], right[right_key]
    else:
        left["_join_key"] = left[left_key].astype("string").str.strip().str.lower()
        right["_join_key"] = right[right_key].astype("string").str.strip().str.lower()

    empty_keys = int(right["_join_key"].isna().sum())
    if empty_keys:
        right = right[right["_join_key"].notna()]
        log.add("10. Join", "Ignored rows without a key", f"{empty_keys} rows of the second table had no join value", empty_keys)

    repeated = int(right["_join_key"].duplicated().sum())
    if repeated:
        if not keep_first:
            raise ValueError(f"The second table repeats {repeated} join values, so the join would create extra rows. "
                             "Tick 'keep first match' in the sidebar to continue.")
        right = right.drop_duplicates("_join_key", keep="first")
        log.add("10. Join", "Kept first match only", f"{repeated} repeated keys in the second table", repeated)

    right["_right_key_value"] = right[right_key]
    right = right.drop(columns=[right_key])
    right = right.rename(columns={c: f"{c}_second" for c in right.columns
                                  if c in left.columns and c != "_join_key"})

    orphans_right = int((~right["_join_key"].isin(left["_join_key"])).sum())
    merged = left.merge(right, on="_join_key", how=how, indicator=True)

    only_right = merged["_merge"] == "right_only"
    if only_right.any():
        merged.loc[only_right, left_key] = merged.loc[only_right, "_right_key_value"]
    unmatched_left = int((merged["_merge"] == "left_only").sum())
    merged = merged.drop(columns=["_join_key", "_right_key_value", "_merge"])

    # reconcile: totals of the main table's numbers must not change
    mismatches = []
    for col in left.columns:
        if col != "_join_key" and is_number_column(left[col]):
            if abs(float(left[col].sum()) - float(merged[col].sum())) > 1e-6:
                mismatches.append(col)

    info = {
        "rows_main": rows_left, "rows_after": len(merged),
        "main_rows_without_match": unmatched_left,
        "second_rows_without_match": orphans_right,
        "totals_match": not mismatches, "mismatched_columns": mismatches,
    }
    log.add("10. Join", "Joined tables",
            f"{rows_left} -> {len(merged)} rows; {unmatched_left} main rows had no match; "
            f"totals {'match' if not mismatches else 'DO NOT match'}", len(merged))
    return merged, info
