import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

# สร้างข้อมูลจำลอง
np.random.seed(42)
num_rows = 1000
days = ['Day1', 'Day2', 'Day3']
guest_types = ['Walk In', 'In House']
df_list = []
for day in days:
    n = num_rows // len(days)
    day_data = {
        'service_no.': range(1, n+1),
        'pax': np.random.randint(1, 6, n),
        'queue_start': pd.to_datetime(['07:00:00'] * n) + pd.to_timedelta(np.random.randint(0, 180, n), unit='m'),
        'queue_end': pd.to_datetime(['07:00:00'] * n) + pd.to_timedelta(np.random.randint(0, 180, n), unit='m'),
        'table_no.': np.random.randint(1, 50, n),
        'meal_start': pd.to_datetime(['08:00:00'] * n) + pd.to_timedelta(np.random.randint(0, 240, n), unit='m'),
        'meal_end': pd.to_datetime(['08:00:00'] * n) + pd.to_timedelta(np.random.randint(60, 300, n), unit='m'),
        'Guest_type': np.random.choice(guest_types, n)
    }
    df_day = pd.DataFrame(day_data)
    df_day['Day'] = day
    df_list.append(df_day)
df_all = pd.concat(df_list, ignore_index=True)
# สำหรับโค้ดใหม่
df_all['meal_start_str'] = df_all['meal_start'].dt.strftime('%H:%M:%S')
df_all['meal_end_str'] = df_all['meal_end'].dt.strftime('%H:%M:%S')

st.title("🍽️ Busy Buffet Analytics Dashboard")

tab1, tab2 = st.tabs(["Dashboard", "Cap Time Analysis"])

with tab1:
    st.markdown("แดชบอร์ดสรุปผลการวิเคราะห์ข้อมูลลูกค้า การรอคิว และระยะเวลาทานอาหาร")
    all_sheets = {day: group.drop(columns=['meal_start_str', 'meal_end_str']) for day, group in df_all.groupby('Day')}
    cols = ['service_no.', 'pax', 'queue_start', 'queue_end', 'table_no.', 'meal_start', 'meal_end', 'Guest_type']
    dfs = []
    st.header("📊 Per-sheet Analytics (สรุปผลรายวัน)")

    for sheet_name, df_temp in all_sheets.items():
        use_cols = [c for c in cols if c in df_temp.columns]
        df_temp = df_temp[use_cols].copy()
        df_temp['Day'] = sheet_name

        if 'Guest_type' in df_temp.columns:
            df_temp['Guest_type'] = df_temp['Guest_type'].astype(str).str.strip().str.title()
            df_temp = df_temp[df_temp['Guest_type'].isin(['Walk In', 'In House'])]

        time_cols = ['queue_start', 'queue_end', 'meal_start', 'meal_end']
        for col in time_cols:
            if col in df_temp.columns:
                df_temp[col] = pd.to_datetime(df_temp[col], errors='coerce')

        df_temp['wait_time_mins'] = (df_temp['queue_end'] - df_temp['queue_start']).dt.total_seconds() / 60
        df_temp['meal_duration_mins'] = (df_temp['meal_end'] - df_temp['meal_start']).dt.total_seconds() / 60
        df_temp.loc[df_temp['meal_duration_mins'] < 0, 'meal_duration_mins'] += 24 * 60
        df_temp['walk_away'] = df_temp['queue_start'].notna() & df_temp['meal_start'].isna()
        df_temp['seated'] = df_temp['meal_start'].notna()

        total_pax = df_temp['pax'].sum()
        total_groups = len(df_temp)
        walk_aways = df_temp['walk_away'].sum()
        avg_wait = df_temp[df_temp['wait_time_mins'] > 0]['wait_time_mins'].mean()

        st.subheader(f"📅 ข้อมูลชีต: {sheet_name}")
        col1, col2, col3 = st.columns(3)
        col1.metric("จำนวนลูกค้าทั้งหมด", f"{total_pax:.0f} คน", f"{total_groups} กลุ่ม")
        col2.metric("กลุ่มที่ทิ้งคิว (Walk-away)", f"{walk_aways} กลุ่ม")
        if pd.notna(avg_wait):
            col3.metric("เวลารอคิวเฉลี่ย", f"{avg_wait:.2f} นาที")
        else:
            col3.metric("เวลารอคิวเฉลี่ย", "ไม่มีการรอคิว")
        st.divider()
        dfs.append(df_temp)

    if len(dfs) == 0:
        st.warning("ไม่พบข้อมูลที่สามารถใช้งานได้หลังจากกรองข้อมูลแล้ว กรุณาตรวจสอบคอลัมน์และประเภทข้อมูลในไฟล์ Excel")
        st.stop()

    df_all_tab1 = pd.concat(dfs, ignore_index=True)
    st.header("📈 Queue Management & Customer Behavior Analytics")
    sns.set_theme(style="whitegrid")

    # Queue Performance
    st.subheader("1. Queue Performance & Customer Attrition Analysis")
    fig1 = plt.figure(figsize=(14, 5))
    plt.subplot(1, 2, 1)
    sns.boxplot(data=df_all_tab1[df_all_tab1['wait_time_mins'] > 0], x='Guest_type', y='wait_time_mins', palette='Set2')
    plt.title('1.1 Overall Wait Time (In-house vs Walk-in)')
    plt.ylabel('Wait Time (Minutes)')

    plt.subplot(1, 2, 2)
    walk_away_counts = df_all_tab1[df_all_tab1['walk_away'] == True]['Guest_type'].value_counts()
    if not walk_away_counts.empty:
        sns.barplot(x=walk_away_counts.index, y=walk_away_counts.values, palette='Reds')
    else:
        plt.text(0.5, 0.5, 'No Walk-aways', ha='center', va='center')
    plt.title('1.2 Overall Walk-aways by Guest Type')
    plt.ylabel('Total Walk-aways (Groups)')
    plt.tight_layout()
    st.pyplot(fig1)

    # Daily Guest Volume
    st.subheader("2. Daily Guest Volume & Peak Demand Analysis")
    fig2 = plt.figure(figsize=(10, 5))
    daily_pax = df_all_tab1.groupby(['Day', 'Guest_type'])['pax'].sum().reset_index()
    sns.barplot(data=daily_pax, x='Day', y='pax', hue='Guest_type', palette='viridis')
    plt.title('2. Total Guests (Pax) Comparison Across Days')
    plt.ylabel('Total Guests (Pax)')
    plt.xlabel('Day (Sheet Name)')
    st.pyplot(fig2)

    # Meal Duration
    st.subheader("3. Meal Duration & Table Occupancy Dynamics")
    df_meal = df_all_tab1[df_all_tab1['seated'] == True].copy()
    duration_cap = df_meal['meal_duration_mins'].quantile(0.99)
    df_meal = df_meal[df_meal['meal_duration_mins'] <= duration_cap]

    fig3 = plt.figure(figsize=(14, 5))
    plt.subplot(1, 2, 1)
    sns.histplot(data=df_meal, x='meal_duration_mins', hue='Guest_type', kde=True, bins=20, palette='Set1', alpha=0.6)
    plt.title('3.1 Meal Duration Distribution (All Days, Outliers Trimmed 99th pct)')
    plt.xlabel('Meal Duration (Minutes)')
    plt.ylabel('Frequency')

    plt.subplot(1, 2, 2)
    sns.violinplot(data=df_meal, x='Guest_type', y='meal_duration_mins', palette='Set1', inner=None)
    sns.stripplot(data=df_meal, x='Guest_type', y='meal_duration_mins', color='k', size=3, alpha=0.45, jitter=0.15)
    plt.title('3.2 Meal Duration Spread (All Days, Outliers Trimmed 99th pct)')
    plt.ylabel('Meal Duration (Minutes)')

    summary_stats = df_meal.groupby('Guest_type')['meal_duration_mins'].agg(['count', 'mean', 'median', 'std']).round(2)
    st.markdown("**สถิติการทานอาหาร (หลังกรอง outliers 99th percentile)**")
    st.dataframe(summary_stats)

    plt.tight_layout()
    st.pyplot(fig3)

    st.header("📌 สถิติภาพรวม (Overall)")
    st.write("**ระยะเวลาทานอาหารเฉลี่ย (นาที) แยกตามประเภทลูกค้า:**")
    st.dataframe(df_all_tab1[df_all_tab1['seated'] == True].groupby('Guest_type')['meal_duration_mins'].mean().round(2))

with tab2:
    df_all['meal_start_dt'] = pd.to_datetime(df_all['meal_start_str'], format='%H:%M:%S', errors='coerce')
    df_all['meal_end_dt'] = pd.to_datetime(df_all['meal_end_str'], format='%H:%M:%S', errors='coerce')
    df_all['actual_duration_mins'] = (df_all['meal_end_dt'] - df_all['meal_start_dt']).dt.total_seconds() / 60
    df_seated = df_all.dropna(subset=['actual_duration_mins']).copy()

    median_duration = df_seated['actual_duration_mins'].median()
    pct_under_120 = (df_seated['actual_duration_mins'] <= 120).mean() * 100
    pct_under_180 = (df_seated['actual_duration_mins'] <= 180).mean() * 100

    st.header("ทำไมการลดเวลา (Cap Seating Time) ถึงไม่เวิร์ก?")
    st.markdown("การจำกัดเวลาจาก 5 ชั่วโมง เหลือ 2-3 ชั่วโมง **ไม่กระทบพฤติกรรมจริงของลูกค้า** และไม่ได้ช่วยแก้ปัญหาช่วงคิวพีก")

    col1, col2, col3 = st.columns(3)
    col1.metric("Median เวลากินจริง", f"{median_duration:.0f} นาที")
    col2.metric("กินจบภายใน 120 นาที", f"{pct_under_120:.1f}%")
    col3.metric("กินจบภายใน 180 นาที", f"{pct_under_180:.1f}%")

    st.divider()

    st.subheader("1. ลูกค้าส่วนใหญ่ใช้เวลาทานเท่าไหร่?")
    fig1 = px.histogram(
        df_seated,
        x="actual_duration_mins",
        nbins=40,
        title="การกระจายตัวของเวลานั่งทานจริง (Meal Duration)",
        labels={'actual_duration_mins': 'ระยะเวลาที่นั่งทาน (นาที)', 'count': 'จำนวนโต๊ะ'},
        color_discrete_sequence=['#1f77b4']
    )
    fig1.add_vline(x=120, line_width=3, line_dash="dash", line_color="red",
                  annotation_text=" Cap 120 นาที (กระทบลูกค้าน้อยมาก)", annotation_position="top right")
    st.plotly_chart(fig1, use_container_width=True)

    st.divider()

    st.subheader("2. จำลองสถานการณ์: ถ้าบังคับออกตอน 120 นาที โต๊ะจะว่างขึ้นไหม?")
    st.markdown("เราจะจำลองยอดการใช้โต๊ะรายนาที (Minute-by-minute) โดยเปรียบเทียบเวลาทานจริง กับ กรณีที่เราบังคับให้ลูกค้าลุกเมื่อครบ 120 นาที")

    def get_active_tables(df, end_col):
        time_range = pd.date_range("1900-01-01 06:00:00", "1900-01-01 12:00:00", freq="1min")
        active_counts = []
        for t in time_range:
            count = ((df['meal_start_dt'] <= t) & (df[end_col] > t)).sum()
            active_counts.append(count)
        return pd.DataFrame({'Time': time_range.time, 'Active_Tables': active_counts})

    df_seated['simulated_end_120'] = df_seated.apply(
        lambda row: row['meal_start_dt'] + pd.Timedelta(minutes=120)
        if row['actual_duration_mins'] > 120
        else row['meal_end_dt'],
        axis=1
    )

    df_actual_active = get_active_tables(df_seated, 'meal_end_dt')
    df_simulated_active = get_active_tables(df_seated, 'simulated_end_120')

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df_actual_active['Time'], y=df_actual_active['Active_Tables'], mode='lines', name='ยอดใช้โต๊ะจากเวลาจริง', line=dict(color='blue', width=3)))
    fig2.add_trace(go.Scatter(x=df_simulated_active['Time'], y=df_simulated_active['Active_Tables'], mode='lines', name='จำลอง Cap ที่ 120 นาที', line=dict(color='red', width=3, dash='dash')))

    fig2.update_layout(
        title="เปรียบเทียบยอดการใช้โต๊ะ (Actual vs 120-min Cap Simulation)",
        xaxis_title="เวลา (Time)",
        yaxis_title="จำนวนโต๊ะที่มีคนนั่ง (Active Tables)",
        hovermode="x unified"
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.info("**ข้อสรุป (Insights):** ปัญหาแท้จริงคือ **Arrival Bunching** (คนแห่มาพร้อมกัน) กราฟแสดงให้เห็นชัดเจนว่าในช่วงพีก (เช่น 08:00 - 09:30) เส้นสีแดงและสีน้ำเงินทับกันสนิท แปลว่าการ Cap เวลาที่ 120 นาที ไม่ได้ช่วยคืนพื้นที่โต๊ะในช่วงเวลาที่วิกฤตที่สุดเลย")


