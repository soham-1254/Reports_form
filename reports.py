import sqlite3
from pathlib import Path
from datetime import date
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import smtplib
from email.message import EmailMessage

# -------------------------------------------------
# EMAIL (SMTP) CONFIG  ⚠️ TEMP: MOVE TO SECRETS LATER
# -------------------------------------------------
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "prakhar.chandel@jute-india.com"
SMTP_PASS = "yees jhwl rnxj jeyy"

EMAIL_TO = [
    "payal.sinha@jute-india.com",
    "soham.panda@jute-india.com"
]

EMAIL_CC = []



# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(page_title="Spool Winding System", layout="wide")

# -------------------------------------------------
# PATH CONFIG
# -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "winding_production.db"
CSV_DIR = DATA_DIR / "csv_backups"
CSV_DIR.mkdir(exist_ok=True)

REPORT_DIR = DATA_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

# -------------------------------------------------
# DB HELPERS
# -------------------------------------------------
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

def insert_row(row):
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
        return pd.read_sql("SELECT * FROM winding_daily ORDER BY id DESC", conn)

init_db()

# -------------------------------------------------
# EMAIL SENDER
# -------------------------------------------------
def send_email(subject, body, attachments):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(EMAIL_TO)
    if EMAIL_CC:
        msg["Cc"] = ", ".join(EMAIL_CC)
    msg["Subject"] = subject
    msg.set_content(body)

    for file_path in attachments:
        with open(file_path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="image",
            subtype="png",
            filename=Path(file_path).name
        )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# -------------------------------------------------
# SIDEBAR NAVIGATION
# -------------------------------------------------
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📝 Daily Entry", "📊 Reports"]
)

# =================================================
# PAGE 1: DAILY ENTRY
# =================================================
if page == "📝 Daily Entry":

    st.title("🧵 Winding – Production Entry")

    with st.form("entry_form"):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 2])

        with c1:
            zone = st.selectbox("Zone *", ["Red", "Green", "Blue", "Yellow", "Other"])
        with c2:
            entry_date = st.date_input("Date *", value=date.today())
        with c3:
            shift = st.selectbox("Shift *", ["A", "B", "C", "General"])
        with c4:
            supervisor_name = st.text_input("Supervisor Name *")

        st.markdown("### Quality & Machine Details")
        d1, d2, d3, d4, d5 = st.columns(5)

        with d1:
            quality = st.number_input("Quality *", min_value=0.0, step=0.5)
        with d2:
            avg_count = st.number_input("Avg Count *", min_value=0.0, step=0.5)
        with d3:
            spindle = st.number_input("Spindle *", min_value=1, step=1)
        with d4:
            no_of_frame = st.number_input("No. of Frame *", min_value=1, step=1)
        with d5:
            no_of_winder = st.number_input("No. of Winder *", min_value=1, step=1)

        st.markdown("### Production")
        p1, p2, p3, p4 = st.columns(4)

        with p1:
            target_prod = st.number_input("Target Prod *", min_value=0, step=1)
        with p2:
            actual_prod = st.number_input("Actual Prod *", min_value=0, step=1)

        diff = actual_prod - target_prod
        kg_per_frame = round(actual_prod / no_of_frame)
        kg_per_winder = round(actual_prod / no_of_winder)

        with p3:
            st.number_input("Kg / Frame", value=kg_per_frame, disabled=True)
        with p4:
            st.number_input("Kg / Winder", value=kg_per_winder, disabled=True)

        submitted = st.form_submit_button("✅ Save Entry")

    if submitted:
        if not supervisor_name.strip():
            st.error("Supervisor Name required")
        elif abs(quality - avg_count) > 0.01:
            st.error("Avg Count must match Quality")
        else:
            insert_row({
                "zone": zone,
                "entry_date": entry_date.isoformat(),
                "shift": shift,
                "supervisor_name": supervisor_name,
                "quality": quality,
                "avg_count": avg_count,
                "spindle": spindle,
                "no_of_frame": no_of_frame,
                "no_of_winder": no_of_winder,
                "target_prod": target_prod,
                "actual_prod": actual_prod,
                "kg_per_frame": kg_per_frame,
                "kg_per_winder": kg_per_winder,
                "diff": diff
            })
            st.success("Saved successfully ✅")

    st.subheader("📄 Saved Data")
    st.dataframe(fetch_all(), use_container_width=True)

def title_case_df(df):
    df = df.copy()
    df.columns = [c.replace("_", " ").title() for c in df.columns]
    return df


def save_img(df, title, path):
    gen_date = date.today().strftime("%d-%b-%Y")

    fig_height = max(6, len(df) * 0.5 + 4)
    fig, ax = plt.subplots(figsize=(16, fig_height))
    ax.axis("off")

    # ---- HEADER ----
    # ---- HEADER ----
    plt.text(
        0.5, 0.97,
        "HASTINGS JUTE MILL",
        ha="center", va="center",
        fontsize=22, fontweight="bold"
    )

    plt.text(
        0.5, 0.90,   # 👈 MORE GAP BELOW MILL NAME
        title,
        ha="center", va="center",
        fontsize=14, fontweight="bold"
    )

    plt.text(
        0.5, 0.86,   # 👈 MORE GAP BELOW REPORT TITLE
        f"Generated on: {gen_date}",
        ha="center", va="center",
        fontsize=10, style="italic"
    )


    # ---- TABLE ----
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc="center",
        cellLoc="center"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.6)

    # ---- FOOTER ----
    plt.text(
        0.5, 0.02,
        "For internal management use only",
        ha="center", va="center",
        fontsize=9, style="italic"
    )

    plt.savefig(path, bbox_inches="tight", dpi=300)
    plt.close()


# =================================================
# PAGE 2: REPORTS
# =================================================
if page == "📊 Reports":

    st.title("📊 Weekly Management Reports")

    df = fetch_all()
    if df.empty:
        st.warning("No data available yet.")
        st.stop()

    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["week"] = df["entry_date"].dt.isocalendar().week
    df["year"] = df["entry_date"].dt.year

    c1, c2 = st.columns(2)
    year = c1.selectbox("Year", sorted(df["year"].unique(), reverse=True))
    week = c2.selectbox("Week", sorted(df[df["year"] == year]["week"].unique()))

    df_curr = df[(df["year"] == year) & (df["week"] == week)]
    df_prev = df[(df["year"] == year) & (df["week"] == week - 1)]

    # -------------------------------------------------
    # REPORT 1: ZONE & QUALITY (WEEKLY COMPARISON)
    # -------------------------------------------------
    st.subheader("📘 Zone & Quality Wise Report (Weekly Comparison)")

    curr_r1 = df_curr.groupby(["zone", "quality"]).agg(
        Kg_Frame=("kg_per_frame", "mean"),
        Kg_Winder=("kg_per_winder", "mean")
    ).reset_index()

    prev_r1 = df_prev.groupby(["zone", "quality"]).agg(
        Prev_Kg_Frame=("kg_per_frame", "mean"),
        Prev_Kg_Winder=("kg_per_winder", "mean")
    ).reset_index()

    r1 = curr_r1.merge(prev_r1, on=["zone", "quality"], how="left")
    r1["Diff Kg/Frame"] = r1["Kg_Frame"] - r1["Prev_Kg_Frame"].fillna(0)
    r1["Diff Kg/Winder"] = r1["Kg_Winder"] - r1["Prev_Kg_Winder"].fillna(0)

    r1 = r1.round(2)
    r1_display = title_case_df(r1)

    st.dataframe(r1_display, use_container_width=True)

    # -------------------------------------------------
    # REPORT 2: ZONE-WISE SUPERVISOR
    # -------------------------------------------------
    st.subheader("📗 Zone-wise Supervisor Report")

    r2 = df_curr.groupby(["zone", "supervisor_name", "quality"]).agg(
        Machines=("no_of_frame", "sum"),
        Kg_Frame=("kg_per_frame", "mean"),
        Kg_Winder=("kg_per_winder", "mean"),
        Difference=("diff", "sum")
    ).reset_index()

    r2 = r2.round(2)
    r2_display = title_case_df(r2)

    st.dataframe(r2_display, use_container_width=True)

    # -------------------------------------------------
    # ACTION BUTTONS
    # -------------------------------------------------
    colA, colB = st.columns(2)

    with colA:
        if st.button("📤 Generate Reports"):
            img1 = REPORT_DIR / f"Zone_Quality_Week_{week}.png"
            img2 = REPORT_DIR / f"Zone_Supervisor_Week_{week}.png"

            save_img(
                r1_display,
                f"Zone & Quality Wise Weekly Report – Week {week}",
                img1
            )

            save_img(
                r2_display,
                f"Zone-wise Supervisor Performance Report – Week {week}",
                img2
            )

            st.success("Reports generated successfully ✅")

            st.image(str(img1))
            st.download_button(
                "⬇️ Download Report 1",
                open(img1, "rb"),
                file_name=img1.name
            )

            st.image(str(img2))
            st.download_button(
                "⬇️ Download Report 2",
                open(img2, "rb"),
                file_name=img2.name
            )

    with colB:
        if st.button("✉️ Email Reports to Management"):
            img1 = REPORT_DIR / f"Zone_Quality_Week_{week}.png"
            img2 = REPORT_DIR / f"Zone_Supervisor_Week_{week}.png"

            if not img1.exists() or not img2.exists():
                st.error("Please generate reports first.")
            else:
                send_email(
                    subject=f"Hastings Jute Mill – Weekly Spool Winding Report (Week {week}, {year})",
                    body=f"""Dear Sir,

Please find attached the weekly Spool Winding reports of Hastings Jute Mill.

1. Zone & Quality-wise report with weekly comparison
2. Zone-wise Supervisor performance report

Regards,
Hastings Jute Mill
""",
                    attachments=[img1, img2]
                )
                st.success("Email sent successfully ✅")

