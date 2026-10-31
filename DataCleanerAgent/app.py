"""Data Cleaner Agent - upload messy data, review a few decisions, download a dashboard-ready file.

Run with:  streamlit run app.py
"""
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from activity_log import ChangeLog
from charts import category_chart, distribution_chart, missing_chart, quality_chart, trend_chart
from cleaning_steps import join_columns, split_column, unpivot_columns
from file_io import build_excel, read_table, sheet_names
from issue_finder import find_issues
from pipeline import finish, prepare
from profiling import basic_facts, column_report, compare_totals, numeric_summary, quality_score
from type_detection import is_number_column, is_text_column, name_looks_like_id

st.set_page_config(page_title="Data Cleaner Agent", page_icon="", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1250px;}
[data-testid="stSidebar"] {background: linear-gradient(180deg, #111936 0%, #0b1020 100%);
       border-right: 1px solid #2a3358;}
.hero {background: linear-gradient(120deg, #4338ca 0%, #7c3aed 50%, #0891b2 100%);
       padding: 26px 34px; border-radius: 20px; margin-bottom: 16px;
       box-shadow: 0 10px 30px rgba(79, 70, 229, 0.35);}
.hero h1 {margin: 0; font-size: 2.3rem; color: white; letter-spacing: -0.5px;}
.hero p {margin: 6px 0 12px 0; color: #e0e7ff; font-size: 1.05rem;}
.chip {display: inline-block; padding: 4px 12px; margin: 0 8px 0 0; border-radius: 999px;
       background: rgba(255,255,255,0.16); color: white; font-size: 0.8rem;}
.stepper {display: flex; gap: 8px; margin-bottom: 18px;}
.stepper div {flex: 1; text-align: center; padding: 9px 4px; border-radius: 12px; font-size: 0.85rem;
       background: #141b34; border: 1px solid #2a3358; color: #8b93b8;}
.stepper .done {background: rgba(34,197,94,0.14); border-color: #22c55e; color: #86efac;}
.stepper .now {background: rgba(99,102,241,0.25); border-color: #818cf8; color: white; font-weight: 600;}
div[data-testid="stMetric"] {background: #141b34; border: 1px solid #2a3358; border-left: 4px solid #6366f1;
       padding: 14px 16px; border-radius: 14px;}
div[data-testid="stMetric"]:nth-child(2n) {border-left-color: #22d3ee;}
div[data-testid="stMetricLabel"] {color: #9aa3c7;}
.step-card {background: linear-gradient(145deg, #141b34, #101731); border: 1px solid #2a3358;
       border-radius: 14px; padding: 14px 16px; height: 100%;}
.step-card b {color: #a5b4fc;}
.ring-card {background: #141b34; border: 1px solid #2a3358; border-radius: 14px; padding: 10px;
       text-align: center; color: #9aa3c7; font-size: 0.85rem;}
button[data-baseweb="tab"] {font-size: 1rem;}
button[kind="primary"] {border-radius: 10px; background: linear-gradient(90deg, #6366f1, #8b5cf6); border: none;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1> Data Cleaner Agent</h1>
  <p>Drop in messy data. Approve a few decisions. Get a file you can load straight into Power BI.</p>
  <span class="chip">12-step pipeline</span><span class="chip">You approve every deletion</span>
  <span class="chip">CSV + Excel output</span><span class="chip">Full change log</span>
</div>
""", unsafe_allow_html=True)


def score_ring(title, value, color):
    circumference = 2 * 3.14159 * 45
    filled = circumference * max(min(value, 100), 0) / 100
    return (f"<div class='ring-card'><svg width='118' height='118' viewBox='0 0 120 120'>"
            f"<circle cx='60' cy='60' r='45' stroke='#2a3358' stroke-width='11' fill='none'/>"
            f"<circle cx='60' cy='60' r='45' stroke='{color}' stroke-width='11' fill='none' stroke-linecap='round' "
            f"stroke-dasharray='{filled:.1f} {circumference:.1f}' transform='rotate(-90 60 60)'/>"
            f"<text x='60' y='67' text-anchor='middle' fill='white' font-size='24' font-weight='700'>{value:.0f}</text>"
            f"</svg><div>{title}</div></div>")


def show_stepper(stage):
    labels = ["1 Upload", "2 Analyse", "3 Decide", "4 Clean", "5 Download"]
    html = "<div class='stepper'>"
    for i, label in enumerate(labels):
        css = "done" if i < stage else ("now" if i == stage else "")
        html += f"<div class='{css}'>{'✔ ' if i < stage else ''}{label}</div>"
    st.markdown(html + "</div>", unsafe_allow_html=True)


for name in ("raw", "prepared", "issues", "join_info", "clean", "log", "settings", "log_mark"):
    st.session_state.setdefault(name, None)


@st.cache_data(show_spinner=False)
def load_table(data, filename, sheet):
    return read_table(data, filename, sheet)


@st.cache_data(show_spinner=False)
def list_sheets(data, filename):
    return sheet_names(data, filename)


def pick_table(label, key):
    uploaded = st.file_uploader(label, type=["csv", "xlsx"], key=f"{key}_file")
    if uploaded is None:
        return None
    data = uploaded.getvalue()
    sheets = list_sheets(data, uploaded.name)
    sheet = st.selectbox("Sheet", sheets, key=f"{key}_sheet") if len(sheets) > 1 else None
    return load_table(data, uploaded.name, sheet)


def forget_decisions():
    for key in [k for k in st.session_state if k.startswith("decision_")]:
        del st.session_state[key]


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("###  Data Cleaner Agent")
    st.caption("Automated data cleaning, 12 steps")
    st.markdown("## 📂 Your data")
    main_df = pick_table("Upload your messy file (CSV or Excel)", "main")

    main_key = second_key = None
    join_how = "left"
    second_df = None
    with st.expander(" Join a second table (optional)"):
        second_df = pick_table("Second file", "second")
        if main_df is not None and second_df is not None:
            main_key = st.selectbox("Join column in main file", list(main_df.columns))
            second_key = st.selectbox("Join column in second file", list(second_df.columns))
            join_how = st.radio("Which rows to keep?", ["left", "outer"], horizontal=True,
                                format_func=lambda v: "All main rows" if v == "left" else "Everything")

    st.markdown(" Settings")
    dayfirst = st.checkbox("Dates are day-first (DD/MM/YYYY)", value=True)
    fill_method = st.radio("Fill missing numbers with", ["median", "mean"], horizontal=True)
    keep_first = st.checkbox("If the second table repeats a key, keep the first match", value=True)

    analyse = st.button(" Analyse my data", type="primary", disabled=main_df is None)

if analyse and main_df is not None:
    log = ChangeLog()
    settings = {"dayfirst": dayfirst, "fill_method": fill_method, "keep_first_match": keep_first,
                "join_how": join_how, "main_key": main_key, "second_key": second_key}
    try:
        with st.spinner("Cleaning the safe stuff and looking for problems..."):
            prepared, issues, join_info = prepare(main_df, second_df, settings, log)
    except ValueError as error:
        st.sidebar.error(str(error))
    else:
        forget_decisions()
        st.session_state.update(raw=main_df, prepared=prepared, issues=issues, join_info=join_info,
                                log=log, settings=settings, clean=None, log_mark=len(log.rows))

state = st.session_state
show_stepper(0 if state.raw is None else (2 if state.clean is None else 4))
tab_profile, tab_decide, tab_result, tab_log = st.tabs(
    [" 1 · Data profile", " 2 · Your decisions", " 3 · Clean result", " 4 · Change log"])

# ------------------------------------------------------------------ tab 1
with tab_profile:
    if state.raw is None:
        st.markdown("### Upload a file in the sidebar to begin")
        st.caption("Everything below happens automatically. You are only asked when data could be lost.")
        steps = [
            ("1 · Profile", "Row counts, types, missing values, summary stats"),
            ("2 · Duplicates", "Exact copies, plus near-copies after spelling is fixed"),
            ("3 · Missing values", "Median / mean for numbers, 'Unknown' for text"),
            ("4 · Data types", "Text to numbers, dates and yes/no; strips ₹ $ and commas"),
            ("5 · Formats", "Trimmed spaces, one casing, one date format"),
            ("6 · Categories", "NY = N.Y. = New York"),
            ("7 · Outliers", "IQR rule - you decide to keep, cap or remove"),
            ("8 · Validation", "No negative quantities, valid emails, dates in order"),
            ("9 · Structure", "Clean column names, unused columns, split / merge / unpivot"),
            ("10 · Join", "Merge a second table and reconcile the totals"),
            ("11 · Derived fields", "Year, month, quarter, age group, profit, margin"),
            ("12 · Document", "Every change is written to the change log"),
        ]
        for start in range(0, 12, 4):
            for column, (title, text) in zip(st.columns(4), steps[start:start + 4]):
                column.markdown(f"<div class='step-card'><b>{title}</b><br>{text}</div>", unsafe_allow_html=True)
            st.write("")
    else:
        raw, facts, score = state.raw, basic_facts(state.raw), quality_score(state.raw)
        cards = st.columns([1.2, 1, 1, 1, 1])
        cards[0].markdown(score_ring("Quality score (before)", score["score"], "#f59e0b"), unsafe_allow_html=True)
        cards[1].metric("Rows", f"{facts['rows']:,}")
        cards[2].metric("Columns", facts["columns"])
        cards[3].metric("Missing cells", f"{facts['missing_cells']:,}", f"{facts['missing_pct']}%", delta_color="off")
        cards[4].metric("Duplicate rows", facts["duplicate_rows"])

        st.markdown("#### Column report")
        st.dataframe(column_report(raw), hide_index=True)
        with st.expander("Raw data preview"):
            st.dataframe(raw.head(25))

        numbers = [c for c in state.prepared.columns if is_number_column(state.prepared[c])]
        if numbers:
            left, right = st.columns([3, 2])
            with left:
                st.markdown("#### Summary statistics (after type fixing)")
                st.dataframe(numeric_summary(state.prepared))
            with right:
                st.markdown("#### Distribution")
                chosen = st.selectbox("Column", numbers)
                figure = distribution_chart(state.prepared[chosen], chosen)
                st.pyplot(figure)
                plt.close(figure)

# ------------------------------------------------------------------ tab 2
with tab_decide:
    if state.prepared is None:
        st.info("Upload a file and press **Analyse my data** first.")
    else:
        prepared, issues = state.prepared, state.issues

        if state.join_info:
            info = state.join_info
            st.markdown("#### 🔗 Join check")
            cols = st.columns(4)
            cols[0].metric("Main rows", info["rows_main"])
            cols[1].metric("Rows after join", info["rows_after"])
            cols[2].metric("Main rows without match", info["main_rows_without_match"])
            cols[3].metric("Totals reconcile", "Yes ✅" if info["totals_match"] else "No ⚠️")

        if issues:
            st.warning(f"{len(issues)} things could remove or change data. Nothing is deleted until you press the button below.")
        else:
            st.success("Nothing risky found. You can go straight to cleaning.")

        for issue in issues:
            with st.container(border=True):
                st.markdown(f"**{issue['title']}**  ·  _{issue['step']}_")
                st.caption(issue["detail"])
                if issue["rows"]:
                    st.dataframe(prepared.loc[issue["rows"]].head(5))
                st.radio("What should I do?", issue["options"],
                         index=issue["options"].index(issue["default"]),
                         key=f"decision_{issue['key']}", horizontal=True)

        if st.button("✅ Apply my decisions and clean", type="primary"):
            decisions = {i["key"]: state[f"decision_{i['key']}"] for i in issues}
            del state.log.rows[state.log_mark:]          # allows pressing the button again
            with st.spinner("Cleaning..."):
                state.clean = finish(prepared, issues, decisions, state.settings, state.log)
            st.success("Done! Open the **Clean result** tab to download your file.")

        with st.expander("🔧 Optional: restructure columns (split, merge, unpivot)"):
            tool = st.selectbox("What do you want to do?", ["Split a column", "Merge columns", "Unpivot wide table"])
            names = list(prepared.columns)
            new_table = None
            if tool == "Split a column":
                column = st.selectbox("Column to split", names)
                delimiter = st.text_input("Split on", " ")
                new_names = st.text_input("New column names (comma separated)", "first_name, last_name")
                if st.button("Split"):
                    new_table = split_column(prepared.copy(), column, delimiter,
                                             [n.strip() for n in new_names.split(",") if n.strip()], state.log)
            elif tool == "Merge columns":
                chosen = st.multiselect("Columns to merge", names)
                separator = st.text_input("Separator", " ")
                new_name = st.text_input("New column name", "merged_column")
                if st.button("Merge") and len(chosen) >= 2:
                    new_table = join_columns(prepared.copy(), chosen, separator, new_name, state.log)
            else:
                id_columns = st.multiselect("Columns to keep as they are", names)
                value_columns = st.multiselect("Columns to turn into rows", [n for n in names if n not in id_columns])
                var_name = st.text_input("Name for the old column headers", "category")
                value_name = st.text_input("Name for the values", "value")
                if st.button("Unpivot") and value_columns:
                    new_table = unpivot_columns(prepared.copy(), id_columns, value_columns, var_name, value_name, state.log)
            if new_table is not None:
                new_table = new_table.reset_index(drop=True)
                forget_decisions()
                state.update(prepared=new_table, issues=find_issues(new_table), clean=None, log_mark=len(state.log.rows))
                st.rerun()

# ------------------------------------------------------------------ tab 3
with tab_result:
    if state.clean is None:
        st.info("Apply your decisions in step 2 to see the cleaned data here.")
    else:
        clean = state.clean
        before, after = quality_score(state.raw), quality_score(clean)
        remaining_blank = int(clean.isna().sum().sum())

        cards = st.columns([1.2, 1.2, 1, 1, 1])
        cards[0].markdown(score_ring("Score before", before["score"], "#f59e0b"), unsafe_allow_html=True)
        cards[1].markdown(score_ring("Score after", after["score"], "#22c55e"), unsafe_allow_html=True)
        cards[2].metric("Rows", f"{len(clean):,}", f"{len(clean) - len(state.raw):+,}", delta_color="off")
        cards[3].metric("Columns", clean.shape[1], f"{clean.shape[1] - state.raw.shape[1]:+d}", delta_color="off")
        cards[4].metric("Blank cells left", remaining_blank)
        if remaining_blank:
            blanks = clean.isna().sum()
            st.caption("Still blank (left on purpose - dates and ids are never guessed): "
                       + ", ".join(f"{c} ({n})" for c, n in blanks[blanks > 0].items()))

        left, right = st.columns(2)
        with left:
            figure = quality_chart(before, after)
            st.pyplot(figure)
            plt.close(figure)
        with right:
            figure = missing_chart(state.prepared, clean)
            if figure is None:
                st.success("No missing values before or after filling.")
            else:
                st.pyplot(figure)
                plt.close(figure)

        st.markdown("#### Does everything still add up?")
        st.caption(f"Compared before and after your decisions: {len(state.prepared):,} rows → {len(clean):,} rows. "
                   "Small changes in totals come from capped, removed or filled values.")
        st.dataframe(compare_totals(state.prepared, clean), hide_index=True)

        st.markdown("#### 📊 Quick dashboard preview")
        st.caption("A taste of what the clean file gives you in Power BI - no extra cleaning needed.")
        categories = [c for c in clean.columns if is_text_column(clean[c]) and 2 <= clean[c].nunique() <= 20]
        dates = [c for c in clean.columns if pd.api.types.is_datetime64_any_dtype(clean[c])]
        measures = [c for c in clean.columns if is_number_column(clean[c]) and not name_looks_like_id(c)
                    and not c.endswith(("_year", "_month"))]
        dash_left, dash_right = st.columns(2)
        with dash_left:
            if categories:
                chosen = st.selectbox("Count rows by", categories, key="dash_category")
                figure = category_chart(clean[chosen], chosen)
                st.pyplot(figure)
                plt.close(figure)
        with dash_right:
            if dates and measures:
                pick_date = st.selectbox("Date column", dates, key="dash_date")
                pick_value = st.selectbox("Monthly total of", measures, key="dash_value")
                figure = trend_chart(clean, pick_date, pick_value)
                if figure is not None:
                    st.pyplot(figure)
                    plt.close(figure)

        st.markdown("#### Clean data")
        st.dataframe(clean.head(100))

        summary = pd.DataFrame({
            "measure": ["Rows", "Columns", "Quality score", "Completeness", "No duplicates", "Correct types"],
            "before": [len(state.raw), state.raw.shape[1], before["score"], before["Completeness"],
                       before["No duplicates"], before["Correct types"]],
            "after": [len(clean), clean.shape[1], after["score"], after["Completeness"],
                      after["No duplicates"], after["Correct types"]],
        })
        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Download CSV", clean.to_csv(index=False).encode("utf-8-sig"),
                           "clean_data.csv", "text/csv")
        d2.download_button("⬇️ Download Excel (data + log + summary)",
                           build_excel(clean, state.log.to_frame(), summary), "clean_data.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ------------------------------------------------------------------ tab 4
with tab_log:
    if state.log is None or not state.log.rows:
        st.info("The change log appears here once your data has been analysed.")
    else:
        log_frame = state.log.to_frame()
        st.caption(f"{len(log_frame)} actions recorded. Every row removed or changed shows up here.")
        st.dataframe(log_frame, hide_index=True)
        st.download_button("⬇️ Download change log (CSV)", log_frame.to_csv(index=False).encode("utf-8-sig"),
                           "change_log.csv", "text/csv")
