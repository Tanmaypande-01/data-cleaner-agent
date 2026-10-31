# Data Cleaner Agent - automatic data cleaning tool

Upload a messy CSV/Excel file, answer a few questions, download a clean file
that loads straight into Power BI. Built with Python, pandas, NumPy,
Seaborn/Matplotlib and Excel output. The interface uses Streamlit (pure Python).

## Run it
```
pip install -r requirements.txt
streamlit run app.py
```
Try it with `sample_data/messy_sales.csv` (and `customer_segments.csv` as the second table,
join on "Customer ID" / "customer id"). Regenerate samples with `python make_sample_data.py`.

## Where each of the 12 steps lives
| Step | File |
|------|------|
| 1 Profile | profiling.py |
| 2 Duplicates | issue_finder.py |
| 3 Missing values | cleaning_steps.py (fill_missing_values) |
| 4 Data types | cleaning_steps.py (fix_data_types) |
| 5 Formats | cleaning_steps.py (clean_text_cells, standardize_case) |
| 6 Categories | cleaning_steps.py (merge_category_variants) |
| 7 Outliers | issue_finder.py (IQR rule) |
| 8 Validation | issue_finder.py |
| 9 Structure | cleaning_steps.py + issue_finder.py |
| 10 Join | merge_tables.py |
| 11 Derived fields | cleaning_steps.py (add_derived_fields) |
| 12 Document | activity_log.py, change log tab and Excel sheet |

## Permission rule
Safe fixes (spaces, casing, types, filling blanks) run automatically and are logged.
Anything that removes rows/columns or changes real values (duplicates, outliers,
invalid values, useless columns) is shown first and only applied after you press
"Apply my decisions".

## Known limits (good to mention in an interview)
- Dates like 03/04/2024 are ambiguous, so there is a day-first / month-first setting.
- Fuzzy category matching is deliberately conservative; add your own labels to KNOWN_ALIASES.
- Only whole-file rules are used. Business-specific checks need new rules in issue_finder.py.
