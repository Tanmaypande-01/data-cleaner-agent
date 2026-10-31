"""Glue code: phase 1 does the safe work and finds questions, phase 2 applies the answers."""
from cleaning_steps import (
    add_derived_fields, clean_text_cells, fill_missing_values, fix_data_types,
    merge_category_variants, standardize_case, tidy_column_names, tidy_name, tidy_number_types,
)
from issue_finder import apply_decisions, find_issues
from merge_tables import merge_tables


def run_safe_steps(df, log, dayfirst):
    df = tidy_column_names(df, log)
    df = clean_text_cells(df, log)
    df = fix_data_types(df, log, dayfirst)
    df = standardize_case(df, log)
    df = merge_category_variants(df, log)
    return df


def prepare(main_df, lookup_df, settings, log):
    """Phase 1 - everything that cannot lose data, then a list of things to ask about."""
    df = run_safe_steps(main_df.copy(), log, settings["dayfirst"])
    join_info = None

    if lookup_df is not None:
        log.context = "second table"
        extra = run_safe_steps(lookup_df.copy(), log, settings["dayfirst"])
        log.context = ""
        df, join_info = merge_tables(
            df, extra, tidy_name(settings["main_key"]), tidy_name(settings["second_key"]),
            settings["join_how"], settings["keep_first_match"], log)

    df = df.reset_index(drop=True)
    return df, find_issues(df), join_info


def finish(prepared, issues, decisions, settings, log):
    """Phase 2 - apply what the user approved, fill gaps, add the new columns."""
    df = apply_decisions(prepared, issues, decisions, log)
    df = fill_missing_values(df, log, settings["fill_method"])
    df = add_derived_fields(df, log)
    df = tidy_number_types(df)
    return df.reset_index(drop=True)
