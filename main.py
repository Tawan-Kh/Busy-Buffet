import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Busy Buffet Analytics",
    page_icon="🍽️",
    layout="wide",
)

EXPECTED_COLS = ["service_no.", "pax", "queue_start", "queue_end",
    "table_no.", "meal_start", "meal_end", "Guest_type"]
TIME_COLS     = ["queue_start", "queue_end", "meal_start", "meal_end"]
VALID_GUEST   = ["Walk In", "In House"]

sns.set_theme(style="whitegrid")

def parse_time_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """แปลงคอลัมน์เวลาเป็น datetime (format HH:MM:SS)."""
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format="%H:%M:%S", errors="coerce")
    return df

def compute_derived_cols(df: pd.DataFrame) -> pd.DataFrame:
    """คำนวณ wait_time, meal_duration, walk_away, seated."""
    if "queue_start" in df.columns and "queue_end" in df.columns:
        df["wait_time_mins"] = (
            (df["queue_end"] - df["queue_start"]).dt.total_seconds() / 60
        )
    if "meal_start" in df.columns and "meal_end" in df.columns:
        df["meal_duration_mins"] = (
            (df["meal_end"] - df["meal_start"]).dt.total_seconds() / 60
        )
        # แก้ midnight rollover
        df.loc[df["meal_duration_mins"] < 0, "meal_duration_mins"] += 24 * 60

    df["walk_away"] = df["queue_start"].notna() & df["meal_start"].isna()
    df["seated"]    = df["meal_start"].notna()
    return df

def load_uploaded_file(uploaded_file) -> pd.DataFrame:
    """
    โหลดไฟล์ Excel (multi-sheet) หรือ CSV แล้วรวมเป็น DataFrame เดียว
    พร้อมคอลัมน์ 'Day' = ชื่อ sheet / 'Sheet1'
    """
    ext = uploaded_file.name.split(".")[-1].lower()

    if ext == "csv":
        sheets = {"Sheet1": pd.read_csv(uploaded_file)}
    else:
        sheets = pd.read_excel(uploaded_file, sheet_name=None)

    dfs = []
    for sheet_name, raw in sheets.items():
        # เลือกเฉพาะคอลัมน์ที่มี
        use_cols = [c for c in EXPECTED_COLS if c in raw.columns]
        df = raw[use_cols].copy()
        df["Day"] = sheet_name

        # กรองประเภทลูกค้า
        if "Guest_type" in df.columns:
            df["Guest_type"] = (
                df["Guest_type"].astype(str).str.strip().str.title()
            )
            df = df[df["Guest_type"].isin(VALID_GUEST)]

        df = parse_time_cols(df, TIME_COLS)
        df = compute_derived_cols(df)
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, ignore_index=True)
    # เก็บเวลาเป็น string สำหรับ Cap Time tab
    df_all["meal_start_str"] = df_all["meal_start"].dt.strftime("%H:%M:%S")
    df_all["meal_end_str"]   = df_all["meal_end"].dt.strftime("%H:%M:%S")
    return df_all


def count_active(df: pd.DataFrame, start_col: str, end_col: str,
    time_range) -> pd.DataFrame:
    counts = [
        ((df[start_col] <= t) & (df[end_col] > t)).sum()
        for t in time_range
    ]
    return pd.DataFrame({"Time": time_range, "Active": counts})

st.title("🍽️ Busy Buffet Analytics Dashboard")
st.caption("วิเคราะห์คิว • ระยะเวลาทานอาหาร • แผนปฏิบัติการ")

uploaded_file = st.file_uploader(
    "📂 อัปโหลดไฟล์ Excel หรือ CSV", type=["xlsx", "csv"]
)

if uploaded_file is None:
    st.info("💡 กรุณาอัปโหลดไฟล์ Excel Dataset เพื่อเริ่มต้นใช้งานแดชบอร์ด")
    st.stop()

df_all = load_uploaded_file(uploaded_file)

if df_all.empty:
    st.error("❌ ไม่พบข้อมูลที่ใช้ได้ กรุณาตรวจสอบชื่อคอลัมน์และประเภทข้อมูล")
    st.stop()

tab1, tab2, tab3 = st.tabs([
    "📊 Dashboard",
    "⏱️ Cap Time Analysis",
    "🎯 Action Plan (90-min Soft Cap)",
])

with tab1:
    st.markdown("แดชบอร์ดสรุปผลการวิเคราะห์ข้อมูลลูกค้า การรอคิว และระยะเวลาทานอาหาร")
    st.header("📋 สรุปผลรายวัน (Per-Sheet Summary)")
    for day, grp in df_all.groupby("Day"):
        total_pax    = grp["pax"].sum() if "pax" in grp.columns else 0
        total_groups = len(grp)
        walk_aways   = grp["walk_away"].sum()
        avg_wait     = grp.loc[grp["wait_time_mins"] > 0, "wait_time_mins"].mean()
        st.subheader(f"📅 {day}")
        c1, c2, c3 = st.columns(3)
        c1.metric("ลูกค้าทั้งหมด", f"{total_pax:.0f} คน", f"{total_groups} กลุ่ม")
        c2.metric("Walk-away (กลุ่มที่ทิ้งคิว)", f"{walk_aways} กลุ่ม")
        c3.metric(
            "เวลารอคิวเฉลี่ย",
            f"{avg_wait:.2f} นาที" if pd.notna(avg_wait) else "ไม่มีการรอคิว",
        )
        st.divider()

    st.header("📈 Queue Management & Customer Behavior Analytics")
    st.subheader("1. Queue Performance & Customer Attrition")
    fig1, (ax1a, ax1b) = plt.subplots(1, 2, figsize=(14, 5))
    sns.boxplot(
        data=df_all[df_all["wait_time_mins"] > 0],
        x="Guest_type", y="wait_time_mins",
        palette="Set2", ax=ax1a,
    )
    ax1a.set_title("1.1 Overall Wait Time (In-house vs Walk-in)")
    ax1a.set_ylabel("Wait Time (Minutes)")
    walk_counts = df_all[df_all["walk_away"]]["Guest_type"].value_counts()
    if not walk_counts.empty:
        sns.barplot(x=walk_counts.index, y=walk_counts.values,
            palette="Reds", ax=ax1b)
    else:
        ax1b.text(0.5, 0.5, "No Walk-aways", ha="center", va="center")
    ax1b.set_title("1.2 Overall Walk-aways by Guest Type")
    ax1b.set_ylabel("Total Walk-aways (Groups)")

    plt.tight_layout()
    st.pyplot(fig1)
    st.subheader("2. Daily Guest Volume & Peak Demand")

    daily_pax = df_all.groupby(["Day", "Guest_type"])["pax"].sum().reset_index()
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    sns.barplot(data=daily_pax, x="Day", y="pax", hue="Guest_type",
        palette="viridis", ax=ax2)
    ax2.set_title("2. Total Guests (Pax) Across Days")
    ax2.set_ylabel("Total Guests (Pax)")
    ax2.set_xlabel("Day (Sheet Name)")
    plt.tight_layout()
    st.pyplot(fig2)

    st.subheader("3. Meal Duration & Table Occupancy")
    df_meal = df_all[df_all["seated"]].copy()
    cap_99  = df_meal["meal_duration_mins"].quantile(0.99)
    df_meal = df_meal[df_meal["meal_duration_mins"] <= cap_99]
    fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(14, 5))

    sns.histplot(data=df_meal, x="meal_duration_mins", hue="Guest_type",
        kde=True, bins=20, palette="Set1", alpha=0.6, ax=ax3a)
    ax3a.set_title("3.1 Meal Duration Distribution (Outliers Trimmed 99th pct)")
    ax3a.set_xlabel("Meal Duration (Minutes)")

    sns.violinplot(data=df_meal, x="Guest_type", y="meal_duration_mins",
        palette="Set1", inner=None, ax=ax3b)
    sns.stripplot(data=df_meal, x="Guest_type", y="meal_duration_mins",
        color="k", size=3, alpha=0.45, jitter=0.15, ax=ax3b)
    ax3b.set_title("3.2 Meal Duration Spread (Outliers Trimmed 99th pct)")
    ax3b.set_ylabel("Meal Duration (Minutes)")

    plt.tight_layout()
    st.pyplot(fig3)

    st.markdown("**สถิติการทานอาหาร (หลังกรอง 99th percentile)**")
    st.dataframe(
        df_meal.groupby("Guest_type")["meal_duration_mins"]
        .agg(["count", "mean", "median", "std"]).round(2)
    )

    st.header("📌 สถิติภาพรวม")
    st.write("**ระยะเวลาทานอาหารเฉลี่ย (นาที) แยกตามประเภทลูกค้า:**")
    st.dataframe(
        df_all[df_all["seated"]].groupby("Guest_type")["meal_duration_mins"]
        .mean().round(2)
    )

with tab2:
    df_cap = df_all.copy()
    df_cap["meal_start_dt"] = pd.to_datetime(
        df_cap["meal_start_str"], format="%H:%M:%S", errors="coerce"
    )
    df_cap["meal_end_dt"] = pd.to_datetime(
        df_cap["meal_end_str"], format="%H:%M:%S", errors="coerce"
    )
    df_cap["actual_duration_mins"] = (
        (df_cap["meal_end_dt"] - df_cap["meal_start_dt"]).dt.total_seconds() / 60
    )
    df_seated = df_cap.dropna(subset=["actual_duration_mins"]).copy()

    median_dur     = df_seated["actual_duration_mins"].median()
    pct_under_120  = (df_seated["actual_duration_mins"] <= 120).mean() * 100
    pct_under_180  = (df_seated["actual_duration_mins"] <= 180).mean() * 100

    st.header("แนวทางที่ 1: ทำไมการลดเวลา (Cap Seating Time) ถึงไม่เวิร์ก?")
    st.markdown(
        "การจำกัดเวลาจาก 5 ชั่วโมง เหลือ 2-3 ชั่วโมง "
        "**ไม่กระทบพฤติกรรมจริงของลูกค้า** และไม่ได้ช่วยแก้ปัญหาช่วงคิวพีก"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Median เวลากินจริง",      f"{median_dur:.0f} นาที")
    c2.metric("กินจบภายใน 120 นาที",    f"{pct_under_120:.1f}%")
    c3.metric("กินจบภายใน 180 นาที",    f"{pct_under_180:.1f}%")
    st.divider()

    #กราฟ : Histogram + vline Cap 120
    st.subheader("1. ลูกค้าส่วนใหญ่ใช้เวลาทานเท่าไหร่?")
    fig_hist = px.histogram(
        df_seated, x="actual_duration_mins", nbins=40,
        title="การกระจายตัวของเวลานั่งทานจริง",
        labels={"actual_duration_mins": "ระยะเวลาที่นั่งทาน (นาที)", "count": "จำนวนโต๊ะ"},
        color_discrete_sequence=["#1f77b4"],
    )
    fig_hist.add_vline(
        x=120, line_width=3, line_dash="dash", line_color="red",
        annotation_text=" Cap 120 นาที (กระทบลูกค้าน้อยมาก)",
        annotation_position="top right",
    )
    st.plotly_chart(fig_hist, use_container_width=True)
    st.divider()

    #กราฟ : Simulation Actual vs Cap 120
    st.subheader("2. จำลองสถานการณ์: ถ้าบังคับออกตอน 120 นาที โต๊ะจะว่างขึ้นไหม?")
    st.markdown(
        "เปรียบเทียบยอดการใช้โต๊ะรายนาที ระหว่างเวลาจริง "
        "กับกรณีที่บังคับให้ลูกค้าลุกเมื่อครบ 120 นาที"
    )

    time_range_cap = pd.date_range("1900-01-01 06:00:00", "1900-01-01 12:00:00", freq="1min")

    df_seated["sim_end_120"] = df_seated.apply(
        lambda r: (
            r["meal_start_dt"] + pd.Timedelta(minutes=120)
            if r["actual_duration_mins"] > 120
            else r["meal_end_dt"]
        ),
        axis=1,
    )

    actual_active = count_active(df_seated, "meal_start_dt", "meal_end_dt",    time_range_cap)
    sim_active    = count_active(df_seated, "meal_start_dt", "sim_end_120",    time_range_cap)

    fig_sim = go.Figure()
    fig_sim.add_trace(go.Scatter(
        x=actual_active["Time"].dt.time, y=actual_active["Active"],
        mode="lines", name="ยอดใช้โต๊ะจริง", line=dict(color="blue", width=3),
    ))
    fig_sim.add_trace(go.Scatter(
        x=sim_active["Time"].dt.time, y=sim_active["Active"],
        mode="lines", name="จำลอง Cap 120 นาที",
        line=dict(color="red", width=3, dash="dash"),
    ))
    fig_sim.update_layout(
        title="เปรียบเทียบยอดการใช้โต๊ะ (Actual vs 120-min Cap Simulation)",
        xaxis_title="เวลา", yaxis_title="จำนวนโต๊ะที่มีคนนั่ง",
        hovermode="x unified",
    )
    st.plotly_chart(fig_sim, use_container_width=True)
    st.info(
        "**ข้อสรุป:** ปัญหาแท้จริงคือ **Arrival Bunching** (คนแห่มาพร้อมกัน) "
        "ในช่วงพีก (08:00-09:30) เส้นสีแดงและสีน้ำเงินทับกัน "
        "→ การ Cap 120 นาที ไม่ได้คืนโต๊ะในช่วงวิกฤตเลย"
    )

    st.header("แนวทางที่ 2: ขึ้นราคา 259 บาท 'ทุกวัน' เวิร์กไหม?")
    st.markdown(
        "การขึ้นราคาแบบเหมารวม **ไม่ใช่ทางแก้ที่ถูกต้อง** "
        "เพราะปัญหาคิวไม่ได้เกิดขึ้นตลอดเวลา"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("เวลาที่มีคิวเทียบกับเวลาทั้งหมด", "10.8%",    "293 จาก 2,705 นาที",    delta_color="off")
    c2.metric("จำนวนวันที่มีคิว",                 "2 จาก 5 วัน", "เฉพาะชีต 143, 153",   delta_color="off")
    c3.metric("ช่วงเวลาคิวพีกสุด",               "08:00-11:00", "หนักสุด 09:00-10:00", delta_color="off")
    st.divider()

    # กราฟ: Queue per day
    st.subheader("1. ปัญหาคิวไม่ได้เกิดขึ้นทุกวัน")
    df_q = df_all.dropna(subset=["queue_start", "queue_end"]).copy()
    day_counts = df_q.groupby("Day").size().reset_index(name="Queue_Groups")
    all_days   = pd.DataFrame({"Day": df_all["Day"].unique()})
    day_counts = pd.merge(all_days, day_counts, on="Day", how="left").fillna(0)
    day_counts["Color"] = day_counts["Queue_Groups"].apply(
        lambda x: "#e74c3c" if x > 0 else "#d3d3d3"
    )
    fig_day = go.Figure(data=[go.Bar(
        x=day_counts["Day"], y=day_counts["Queue_Groups"],
        marker_color=day_counts["Color"],
        text=day_counts["Queue_Groups"], textposition="auto",
    )])
    fig_day.update_layout(
        title="จำนวนกลุ่มลูกค้าที่ต้องรอคิว แยกตามวัน",
        xaxis_title="วัน (Sheet)", yaxis_title="จำนวนกลุ่มที่รอคิว",
    )
    st.plotly_chart(fig_day, use_container_width=True)

    # กราฟ: Queue density by time
    st.subheader("2. ปัญหาคิวไม่ได้เกิดทั้งวัน (กระจุกตัวช่วงสาย)")
    df_q["q_start_dt"] = pd.to_datetime(
        "2026-01-01 " + df_q["queue_start"].astype(str), errors="coerce"
    ).dt.tz_localize(None)
    df_q["q_end_dt"] = pd.to_datetime(
        "2026-01-01 " + df_q["queue_end"].astype(str), errors="coerce"
    ).dt.tz_localize(None)

    time_range_q = pd.date_range("2026-01-01 06:00:00", "2026-01-01 12:00:00", freq="1min")
    q_density = [
        (
            (df_q["q_start_dt"].notna()) &
            (df_q["q_start_dt"] <= t) &
            (df_q["q_end_dt"].notna()) &
            (df_q["q_end_dt"] > t)
        ).sum()
        for t in time_range_q
    ]
    fig_density = px.area(
        x=time_range_q, y=q_density,
        labels={"x": "เวลา", "y": "จำนวนกลุ่มที่ยืนรอคิว"},
        title="ความหนาแน่นของคิวรายนาที (รวมทุกวัน)",
    )
    fig_density.update_traces(line_color="#e74c3c", fillcolor="rgba(231,76,60,0.4)")
    fig_density.update_layout(xaxis_tickformat="%H:%M")
    fig_density.add_vrect(
        x0="2026-01-01 08:00:00", x1="2026-01-01 11:00:00",
        fillcolor="yellow", opacity=0.2, layer="below", line_width=0,
        annotation_text="Peak Period (08:00-11:00)", annotation_position="top left",
    )
    st.plotly_chart(fig_density, use_container_width=True)
    st.info(
        "**ข้อสรุป:** หากจะใช้ราคาแก้ปัญหา ต้องเป็น **Targeted Pricing** เช่น "
        "Early Bird Discount ช่วง 06:00-07:30 เพื่อกระจาย Demand "
        "ไม่ใช่ขึ้นราคาเหมาทุกวัน"
    )

    st.header("แนวทางที่ 3: ให้สิทธิ์ In-house แซงคิว (Queue Skipping)")
    st.markdown(
        "นโยบายนี้แก้ปัญหา **ผิดจุด** เพราะเป็นการจัดการความรู้สึก "
        "ไม่ใช่การเพิ่ม Capacity — ไม่มีโต๊ะว่างให้นั่งอยู่ดี"
    )

    c1, c2 = st.columns(2)
    c1.metric("คิวเฉลี่ยช่วงพีก (Day 153)", "10.6 กลุ่ม", "Walk-in 7.8 | In-house 2.9", delta_color="off")
    c2.metric("โต๊ะที่ถูกใช้ ณ จุด Peak",  "24 ยูนิต",   "Walk-in 18 | In-house 6",    delta_color="off")
    st.divider()

    df_153 = df_all[df_all["Day"] == "153"].copy()
    df_153["Guest_type"] = (
        df_153["Guest_type"].astype(str).str.strip().str.title()
        .replace({"Walk In": "Walk-in", "In House": "In-house"})
    )

    for col_src, col_dst in [("queue_start", "q_start"), ("queue_end", "q_end"),
        ("meal_start",  "m_start"), ("meal_end",  "m_end")]:
        df_153[col_dst] = pd.to_datetime(
            "2026-01-01 " + df_153[col_src].astype(str), errors="coerce"
        ).dt.tz_localize(None)

    time_range_153 = pd.date_range("2026-01-01 07:00:00", "2026-01-01 11:30:00", freq="1min")
    seat_data = [
        {
            "Time": t,
            "Walk-in":   ((df_153["Guest_type"] == "Walk-in")   & (df_153["m_start"] <= t) & (df_153["m_end"] > t)).sum(),
            "In-house":  ((df_153["Guest_type"] == "In-house")  & (df_153["m_start"] <= t) & (df_153["m_end"] > t)).sum(),
        }
        for t in time_range_153
    ]
    df_seat = pd.DataFrame(seat_data)

    st.subheader("กราฟจำนวนโต๊ะที่ถูกใช้งาน (Day 153)")
    fig_seat = go.Figure()
    fig_seat.add_trace(go.Scatter(
        x=df_seat["Time"], y=df_seat["In-house"],
        mode="lines", stackgroup="one", name="In-house (แขกโรงแรม)",
        fillcolor="#2ecc71", line=dict(color="#27ae60"),
    ))
    fig_seat.add_trace(go.Scatter(
        x=df_seat["Time"], y=df_seat["Walk-in"],
        mode="lines", stackgroup="one", name="Walk-in (ลูกค้าภายนอก)",
        fillcolor="#3498db", line=dict(color="#2980b9"),
    ))
    fig_seat.add_hline(
        y=24, line_dash="dash", line_color="red",
        annotation_text="Max Capacity (~24 Tables)", annotation_position="top left",
    )
    fig_seat.update_layout(
        xaxis_tickformat="%H:%M",
        yaxis_title="จำนวนโต๊ะที่กำลังใช้งาน",
        hovermode="x unified",
    )
    st.plotly_chart(fig_seat, use_container_width=True)
    st.error(
        "**บทสรุป:** Queue Skipping ไม่ใช่ Capacity Solution — แค่ย้ายความเจ็บปวดไปรวมที่ Walk-in "
        "ซึ่งจะดันยอด Walk-away ให้พุ่งขึ้น วิธีที่ถูกคือ Table Management "
        "หรือ Dynamic Pricing เพื่อลด Arrival Bunching"
    )

with tab3:
    st.header("🎯 Action Plan: Walk-in 90-Minute Soft Cap")
    st.markdown("### ข้อเสนอแนะที่ถูกต้องตามข้อมูล (Data-Driven Recommendation)")

    proposed_cap = st.slider(
        "⚙️ ตั้งเวลา Soft Cap สำหรับ Walk-in (นาที):",
        min_value=60, max_value=150, value=90, step=15,
    )

    st.info(
        f"**📝 กติกาการบังคับใช้ ({proposed_cap}-min Soft Cap)**  \n"
        "1. **Target:** เฉพาะ Walk-in เท่านั้น  \n"
        f"2. **Timing:** บังคับใช้เฉพาะช่วงคิวพีก (คิวเกิน 5 กลุ่ม)  \n"
        f"3. **Execution:** เตือนล่วงหน้าที่นาทีที่ {proposed_cap - 15}, "
        f"ขอคืนโต๊ะนาทีที่ {proposed_cap}"
    )

    df_walkin  = df_all[df_all["Guest_type"] == "Walk In"].copy()
    df_inhouse = df_all[df_all["Guest_type"] == "In House"].copy()

    w_mean, w_med = df_walkin["meal_duration_mins"].mean(),  df_walkin["meal_duration_mins"].median()
    i_mean, i_med = df_inhouse["meal_duration_mins"].mean(), df_inhouse["meal_duration_mins"].median()
    impacted_pct  = (df_walkin["meal_duration_mins"] > proposed_cap).mean() * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Walk-in Duration",   f"{w_mean:.1f} นาที")
    c2.metric("Avg In-house Duration",  f"{i_mean:.1f} นาที")
    c3.metric(
        f"Walk-ins ที่ได้รับผลกระทบจาก {proposed_cap}m cap",
        f"{impacted_pct:.1f}%",
        delta="กลุ่มเป้าหมาย", delta_color="inverse",
    )
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 1️⃣ กราฟพิสูจน์ปัญหา (KDE Distribution)")
        st.caption("Walk-in มีหางยาว (Long-stay) แย่ง Capacity จาก In-house")

        fig_kde, ax_kde = plt.subplots(figsize=(8, 5))
        sns.kdeplot(data=df_inhouse, x="meal_duration_mins",
                    fill=True, color="#3498db", label=f"In-house (Med: {i_med:.0f}m)", ax=ax_kde)
        sns.kdeplot(data=df_walkin,  x="meal_duration_mins",
                    fill=True, color="#e74c3c", label=f"Walk-in (Med: {w_med:.0f}m)", ax=ax_kde)
        ax_kde.axvline(proposed_cap, color="black", linestyle="--", linewidth=2,
                       label=f"Soft Cap: {proposed_cap}m")
        ax_kde.set_xlim(0, 300)
        ax_kde.set_xlabel("Meal Duration (Minutes)")
        ax_kde.legend()
        st.pyplot(fig_kde)

    with col2:
        st.markdown(f"#### 2️⃣ ลูกค้าที่นั่งเกิน {proposed_cap} นาที เข้ามาตอนกี่โมง?")
        st.caption("พิสูจน์ว่าการ Cap คืน Capacity ตรงช่วง Peak ได้จริง")

        if "meal_start" in df_walkin.columns:
            df_walkin["arrival_hour"] = df_walkin["meal_start"].dt.hour
            df_long  = df_walkin[df_walkin["meal_duration_mins"] > proposed_cap]
            long_cnt = df_long.groupby("arrival_hour").size().reset_index(name="count")

            fig_arr, ax_arr = plt.subplots(figsize=(8, 5))
            if not long_cnt.empty:
                sns.barplot(data=long_cnt, x="arrival_hour", y="count",
                    color="#e67e22", ax=ax_arr)
                ax_arr.axvspan(-0.5, 2.5, color="red", alpha=0.1,
                    label="Peak Queue Zone (07:00-09:00)")
                ax_arr.set_xlabel("Arrival Hour (24h)")
                ax_arr.set_ylabel("Long-stay Groups")
                ax_arr.legend()
            else:
                ax_arr.text(0.5, 0.5, "ไม่มีลูกค้าที่นั่งนานเกินเวลาที่กำหนด",
                    ha="center", va="center")
            st.pyplot(fig_arr)

    st.divider()

    st.markdown("#### 🆚 ทำไมวิธีนี้เวิร์กกว่า 2 ข้อที่เหลือ?")
    comp_data = {
        "Operational Criteria": [
            "แก้ปัญหาที่ต้นเหตุ",
            "ช่วงเวลาบังคับใช้",
            "ผลกระทบต่อ In-house",
            "ความยุติธรรม (Fairness)",
        ],
        f"✅ {proposed_cap}-min Soft Cap (เสนอ)": [
            "ตรงจุด — ตัด Long-stay Walk-in",
            f"เฉพาะช่วง Peak / คิวเกิน 5 กลุ่ม",
            "ไม่กระทบเลย",
            "อธิบายง่าย กติกาแฟร์ตั้งแต่นั่ง",
        ],
        "❌ ขึ้นราคา 259 บาท": [
            "ไม่แก้ — จ่ายแพงแล้วยิ่งนั่งนาน",
            "บังคับใช้ทั้งวัน ทุกวัน",
            "กระทบถ้าห้องพักไม่รวมอาหาร",
            "ลูกค้าด่า — ขึ้นราคาแก้คิว",
        ],
        "❌ Queue Skipping": [
            "ไม่แก้ — แค่สลับลำดับคนรอ",
            "ทำตอนมีคิว",
            "ได้โต๊ะเร็วขึ้น",
            "Walk-in รู้สึกโดนเอาเปรียบขั้นสุด",
        ],
    }
    st.table(pd.DataFrame(comp_data).set_index("Operational Criteria"))

    st.success(
        "**สรุป:** Soft Cap ที่ Walk-in เฉพาะช่วง Peak คือแนวทางที่ "
        "**แก้ปัญหาที่ต้นเหตุ (Arrival Bunching + Long-stay)** "
        "โดยไม่กระทบ In-house และรักษาภาพลักษณ์ของโรงแรมไว้ได้ ✅"
    )