# Data Cleaner Agent: automatic data cleaning tool

Upload a messy CSV or Excel file, answer a few questions, and download a clean file that loads straight into Power BI. Built with **Python, pandas, NumPy, Seaborn/Matplotlib** and **Streamlit**.



![Issues found](docs/screenshots/02_issues.png)



## What it does
- Profiles the file, finds duplicates, missing values, wrong data types, messy text, category variants, outliers and invalid values
- Fixes safe things automatically (spaces, casing, types) and logs every change
- **Asks first** before anything that removes rows or changes real values
- Joins a second table (e.g. customer segments) on a key column
- Adds derived fields (year, month, quarter, age group, line total, profit, margin %)
- Exports one Excel file with `clean_data`, `change_log` and a before/after summary

## Example result (sample file)
Input: **154 rows, 14 columns** of messy sales data plus a customer lookup table.
Found **9 issues** (empty rows, duplicates, invalid emails, impossible quantities/ages, unusual prices, ship date before order date).
Output with default decisions: **150 rows, 27 columns**, with **27 logged changes**.

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
Safe fixes run automatically and are logged. Anything that removes rows or columns, or changes real values, is shown first and only applied after you press "Apply my decisions".

## Run it
```
pip install -r requirements.txt
streamlit run app.py
```
Try `sample_data/messy_sales.csv`, with `customer_segments.csv` as the second table (join on "Customer ID" / "customer id"). Regenerate samples with `python make_sample_data.py`.

## Known limits
- Dates like 03/04/2024 are ambiguous, so there is a day-first / month-first setting
- Fuzzy category matching is deliberately conservative; add your own labels to KNOWN_ALIASES
- Only whole-file rules are used; business-specific checks need new rules in issue_finder.py
- Sample data is synthetic

## Author
Tanmay pande  | https://www.linkedin.com/in/tanmay-pande-5558202b9 | tanmaypande321@gamil.com
