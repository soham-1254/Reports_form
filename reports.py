import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Spool Winding Reports", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "winding_production.db"
REPORT_DIR = BASE_DIR / "data" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------ LOAD DATA SAFELY ------------------
def load_data():
    if not DB_PATH.exists():
        st.error("❌ Database not found. Please run app.py and enter data first.")
        st.stop()

    with sqlite3.connect(DB_PATH) as conn:
        try:
            df = pd.read_sql("SELECT * FROM winding_daily", conn)
        except Exception:
            st.error("❌ Table 'winding_daily' not found. Run app.py once.")
            st.stop()

    if df.empty:
        st.warning("⚠ No data available yet.")
        st.stop()

    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["week"] = df["entry_date"].dt.isocalendar().week
    df["year"] = df["entry_date"].dt.year
    return df

df = load_data()

# ------------------ HEADER ------------------
st.title("📊 Spool Winding – Weekly Management Reports")

c1, c2 = st.columns(2)

with c1:
    selected_year = st.selectbox(
        "Select Year",
        sorted(df["year"].unique(), reverse=True)
    )

with c2:
    selected_week = st.selectbox(
        "Select Week",
        sorted(df[df["year"] == selected_year]["week"].unique())
    )

df_curr = df[(df["year"] == selected_year) & (df["week"] == selected_week)]
df_prev = df[(df["year"] == selected_year) & (df["week"] == selected_week - 1)]

# Handle missing previous week safely
if df_prev.empty:
    df_prev = pd.DataFrame(columns=df_curr.columns)

# ------------------ REPORT 1 ------------------
st.subheader("📘 Report-1: Zone & Quality Wise (Weekly Comparison)")

curr_r1 = (
    df_curr.groupby(["zone", "quality"])
    .agg(
        kg_frame=("kg_per_frame", "mean"),
        kg_winder=("kg_per_winder", "mean")
    )
    .reset_index()
)

prev_r1 = (
    df_prev.groupby(["zone", "quality"])
    .agg(
        prev_kg_frame=("kg_per_frame", "mean"),
        prev_kg_winder=("kg_per_winder", "mean")
    )
    .reset_index()
)

r1 = curr_r1.merge(prev_r1, on=["zone", "quality"], how="left")

r1["Diff Kg/Frame"] = r1["kg_frame"] - r1["prev_kg_frame"].fillna(0)
r1["Diff Kg/Winder"] = r1["kg_winder"] - r1["prev_kg_winder"].fillna(0)

st.dataframe(r1.round(2), use_container_width=True)

# ------------------ REPORT 2 ------------------
st.subheader("📗 Report-2: Zone-wise Supervisor Performance")

r2 = (
    df_curr.groupby(["zone", "supervisor_name", "quality"])
    .agg(
        Machines=("no_of_frame", "sum"),
        Kg_Frame=("kg_per_frame", "mean"),
        Kg_Winder=("kg_per_winder", "mean"),
        Difference=("diff", "sum")
    )
    .reset_index()
)

st.dataframe(r2.round(2), use_container_width=True)

# ------------------ IMAGE GENERATOR ------------------
def save_table_image(df, title, path):
    fig, ax = plt.subplots(figsize=(14, len(df) * 0.45 + 2))
    ax.axis("off")

    table = ax.table(
        cellText=df.round(2).values,
        colLabels=df.columns,
        cellLoc="center",
        loc="center"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.4)

    plt.title(title, fontsize=14, fontweight="bold", pad=20)
    plt.savefig(path, bbox_inches="tight", dpi=200)
    plt.close()

# ------------------ GENERATE REPORT BUTTON ------------------
st.divider()

if st.button("📤 Generate WhatsApp-Ready Reports"):
    img_r1 = REPORT_DIR / f"Report1_Week_{selected_week}.png"
    img_r2 = REPORT_DIR / f"Report2_Week_{selected_week}.png"

    save_table_image(
        r1,
        f"Zone & Quality Weekly Report – Week {selected_week}",
        img_r1
    )

    save_table_image(
        r2,
        f"Zone-wise Supervisor Report – Week {selected_week}",
        img_r2
    )

    st.success("✅ Reports generated successfully")

st.subheader("📥 Download Reports")

# ---- Report 1 ----
st.image(str(img_r1))
with open(img_r1, "rb") as f:
    st.download_button(
        label="⬇️ Download Report-1 (Zone & Quality)",
        data=f,
        file_name=img_r1.name,
        mime="image/png"
    )

# ---- Report 2 ----
st.image(str(img_r2))
with open(img_r2, "rb") as f:
    st.download_button(
        label="⬇️ Download Report-2 (Zone Supervisor)",
        data=f,
        file_name=img_r2.name,
        mime="image/png"
    )

