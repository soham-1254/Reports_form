# app.py
import os
import sqlite3
from pathlib import Path
from datetime import date
import pandas as pd
import streamlit as st

# -----------------------------
# CONFIG: storage locations
# -----------------------------
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "winding_production.db"
CSV_DIR = DATA_DIR / "csv_backups"
CSV_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="Spool Winding Daily Entry", layout="wide")

# -----------------------------
# DB helpers
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS winding_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            shift TEXT NOT NULL,
            supervisor_name TEXT NOT NULL,
            quality REAL NOT NULL,
            avg_count REAL NOT NULL,
            spindle INTEGER NOT NULL,
            no_of_frame INTEGER NOT NULL,
            no_of_winder INTEGER NOT NULL,
            target_prod INTEGER NOT NULL,
            actual_prod INTEGER NOT NULL,
            kg_per_frame INTEGER NOT NULL,
            kg_per_winder INTEGER NOT NULL,
            diff INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)
        conn.commit()

def insert_row(row: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO winding_daily (
                zone, entry_date, shift, supervisor_name,
                quality, avg_count, spindle,
                no_of_frame, no_of_winder,
                target_prod, actual_prod,
                kg_per_frame, kg_per_winder, diff
            ) VALUES (
                :zone, :entry_date, :shift, :supervisor_name,
                :quality, :avg_count, :spindle,
                :no_of_frame, :no_of_winder,
                :target_prod, :actual_prod,
                :kg_per_frame, :kg_per_winder, :diff
            );
        """, row)
        conn.commit()

def fetch_all():
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM winding_daily ORDER BY id DESC;", conn)
    return df

init_db()

# -----------------------------
# UI
# -----------------------------
st.title("🧵 Spool Winding Daily Production Form")

with st.expander("📦 Storage Location", expanded=True):
    st.code(f"DB  : {DB_PATH.resolve()}")
    st.code(f"CSV : {CSV_DIR.resolve()}")

st.divider()

# -----------------------------
# Form
# -----------------------------
with st.form("winding_form"):
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

    with c1:
        zone = st.selectbox("Zone *", ["Red", "Green", "Blue", "Yellow", "Other"])
    with c2:
        entry_date = st.date_input("Date *", value=date.today(), format="DD-MM-YYYY")
    with c3:
        shift = st.selectbox("Shift *", ["A", "B", "C", "General"])
    with c4:
        supervisor_name = st.text_input("Supervisor Name *")

    st.markdown("### Quality & Machine Details")
    d1, d2, d3, d4, d5 = st.columns(5)

    with d1:
        quality = st.number_input("Quality *", min_value=0.0, step=0.5)
    with d2:
        avg_count = st.number_input("Avg. Count *", min_value=0.0, step=0.5)
    with d3:
        spindle = st.number_input("Spindle *", min_value=1, step=1)  # NO VALIDATION
    with d4:
        no_of_frame = st.number_input("No. of Frame *", min_value=1, step=1)
    with d5:
        no_of_winder = st.number_input("No. of Winder *", min_value=1, step=1)

    st.markdown("### Production")
    p1, p2, p3, p4 = st.columns(4)

    with p1:
        target_prod = st.number_input("Target Prod. *", min_value=0, step=1)
    with p2:
        actual_prod = st.number_input("Actual Prod. *", min_value=0, step=1)

    diff = actual_prod - target_prod
    kg_per_frame = round(actual_prod / no_of_frame) if no_of_frame > 0 else 0
    kg_per_winder = round(actual_prod / no_of_winder) if no_of_winder > 0 else 0

    with p3:
        st.number_input("Kg / Frame (auto)", value=kg_per_frame, disabled=True)
    with p4:
        st.number_input("Kg / Winder (auto)", value=kg_per_winder, disabled=True)

    st.info(f"Diff (Actual − Target): {diff}")

    submit = st.form_submit_button("✅ Save Entry")

# -----------------------------
# Save logic
# -----------------------------
if submit:
    errors = []

    if not supervisor_name.strip():
        errors.append("Supervisor Name is required.")

    if abs(quality - avg_count) > 0.01:
        errors.append("Avg. Count should match Quality.")

    if errors:
        st.error("Fix the following:")
        for e in errors:
            st.write("•", e)
    else:
        row = {
            "zone": zone,
            "entry_date": entry_date.isoformat(),
            "shift": shift,
            "supervisor_name": supervisor_name.strip(),
            "quality": quality,
            "avg_count": avg_count,
            "spindle": spindle,
            "no_of_frame": no_of_frame,
            "no_of_winder": no_of_winder,
            "target_prod": target_prod,
            "actual_prod": actual_prod,
            "kg_per_frame": kg_per_frame,
            "kg_per_winder": kg_per_winder,
            "diff": diff,
        }

        insert_row(row)

        csv_path = CSV_DIR / f"winding_{entry_date.isoformat()}.csv"
        fetch_all().to_csv(csv_path, index=False)

        st.success("Saved successfully ✅")
        st.code(csv_path.resolve())

st.divider()
st.subheader("📊 Saved Data")
st.dataframe(fetch_all(), use_container_width=True)
