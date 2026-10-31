"""Seaborn / Matplotlib charts, styled to match the dark app theme."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

BG = "#0b1020"
PANEL = "#141b34"
TEXT = "#e5e7eb"
BEFORE_COLOR = "#f97316"
AFTER_COLOR = "#22c55e"
PALETTE = ["#6366f1", "#22d3ee", "#22c55e", "#f59e0b", "#ec4899", "#a78bfa", "#fb7185", "#38bdf8", "#facc15", "#34d399"]


def _style(ax, fig):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_color("#2a3358")
    ax.grid(color="#2a3358", alpha=0.5)
    ax.set_axisbelow(True)


def quality_chart(before, after):
    parts = ["Completeness", "No duplicates", "Correct types", "score"]
    labels = ["Completeness", "No duplicates", "Correct types", "Overall"]
    rows = []
    for key, label in zip(parts, labels):
        rows.append({"part": label, "value": before[key], "stage": "Before"})
        rows.append({"part": label, "value": after[key], "stage": "After"})
    fig, ax = plt.subplots(figsize=(6, 3.4))
    sns.barplot(data=pd.DataFrame(rows), x="part", y="value", hue="stage", ax=ax,
                palette={"Before": BEFORE_COLOR, "After": AFTER_COLOR})
    ax.set_ylim(0, 105)
    ax.set_xlabel("")
    ax.set_ylabel("score")
    ax.set_title("Data quality: before vs after")
    _style(ax, fig)
    legend = ax.legend(facecolor=PANEL, edgecolor="none")
    for text in legend.get_texts():
        text.set_color(TEXT)
    fig.tight_layout()
    return fig


def missing_chart(before_df, after_df):
    both = pd.DataFrame({"Before": before_df.isna().sum(), "After": after_df.isna().sum()}).dropna()
    both = both[(both["Before"] > 0) | (both["After"] > 0)]
    if both.empty:
        return None
    both = both.sort_values("Before", ascending=False).head(10)
    long = both.reset_index(names="column").melt(id_vars="column", var_name="stage", value_name="missing")
    fig, ax = plt.subplots(figsize=(6, max(2.2, 0.55 * len(both) + 1)))
    sns.barplot(data=long, y="column", x="missing", hue="stage", ax=ax,
                palette={"Before": BEFORE_COLOR, "After": AFTER_COLOR})
    ax.set_title("Missing values per column")
    ax.set_ylabel("")
    _style(ax, fig)
    legend = ax.legend(facecolor=PANEL, edgecolor="none")
    for text in legend.get_texts():
        text.set_color(TEXT)
    fig.tight_layout()
    return fig


def distribution_chart(values, title):
    fig, ax = plt.subplots(figsize=(6, 3))
    sns.histplot(values.dropna(), kde=True, color="#6366f1", ax=ax, edgecolor=PANEL)
    ax.set_title(title)
    ax.set_xlabel("")
    _style(ax, fig)
    fig.tight_layout()
    return fig


def category_chart(series, title):
    counts = series.value_counts().head(10).reset_index()
    counts.columns = ["label", "rows"]
    fig, ax = plt.subplots(figsize=(6, max(2.4, 0.45 * len(counts) + 1)))
    sns.barplot(data=counts, y="label", x="rows", hue="label", palette=PALETTE[:len(counts)], legend=False, ax=ax)
    ax.set_title(f"Rows per {title}")
    ax.set_ylabel("")
    _style(ax, fig)
    fig.tight_layout()
    return fig


def trend_chart(df, date_col, value_col):
    monthly = df.dropna(subset=[date_col]).set_index(date_col)[value_col].resample("MS").sum()
    if len(monthly) < 2:
        return None
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.plot(monthly.index, monthly.values, color="#22d3ee", linewidth=2.5, marker="o")
    ax.fill_between(monthly.index, monthly.values, color="#22d3ee", alpha=0.15)
    ax.set_title(f"Monthly total of {value_col}")
    fig.autofmt_xdate()
    _style(ax, fig)
    fig.tight_layout()
    return fig
