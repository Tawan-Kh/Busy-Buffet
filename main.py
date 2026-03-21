import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Busy Buffet Analytics", layout="wide")

st.title("🍽️ Busy Buffet Analytics Dashboard")

uploaded_file = st.file_uploader("อัปโหลดไฟล์ Excel หรือ CSV", type=['xlsx', 'csv'])

if uploaded_file is not None:
    # โหลดข้อมูล
    file_ext = uploaded_file.name.split('.')[-1].lower()
    if file_ext == 'csv':
        all_sheets = {'Sheet1': pd.read_csv(uploaded_file)}
    else:
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
    cols = ['service_no.', 'pax', 'queue_start', 'queue_end', 'table_no.', 'meal_start', 'meal_end', 'Guest_type']
    dfs = []
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
                df_temp[col] = pd.to_datetime(df_temp[col], format='%H:%M:%S', errors='coerce')
        df_temp['wait_time_mins'] = (df_temp['queue_end'] - df_temp['queue_start']).dt.total_seconds() / 60
        df_temp['meal_duration_mins'] = (df_temp['meal_end'] - df_temp['meal_start']).dt.total_seconds() / 60
        df_temp.loc[df_temp['meal_duration_mins'] < 0, 'meal_duration_mins'] += 24 * 60 
        df_temp['walk_away'] = df_temp['queue_start'].notna() & df_temp['meal_start'].isna()
        df_temp['seated'] = df_temp['meal_start'].notna()
        dfs.append(df_temp)
    df_all = pd.concat(dfs, ignore_index=True)
    # สำหรับโค้ดใหม่
    df_all['meal_start_str'] = df_all['meal_start'].dt.strftime('%H:%M:%S')
    df_all['meal_end_str'] = df_all['meal_end'].dt.strftime('%H:%M:%S')
    tab1, tab2 = st.tabs(["Dashboard", "Cap Time Analysis"])
    with tab1:
        st.markdown("แดชบอร์ดสรุปผลการวิเคราะห์ข้อมูลลูกค้า การรอคิว และระยะเวลาทานอาหาร")
        all_sheets = {day: group for day, group in df_all.groupby('Day')}
        cols = ['service_no.', 'pax', 'queue_start', 'queue_end', 'table_no.', 'meal_start', 'meal_end', 'Guest_type']
        dfs = []
        st.header("📊 Per-sheet Analytics (สรุปผลรายวัน)")
        
        for sheet_name, df_temp in all_sheets.items():
            use_cols = [c for c in cols if c in df_temp.columns]
            df_temp = df_temp[use_cols].copy()
            # Day อยู่แล้ว
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
        st.header("📈 Queue Management & Customer Behavior Analytics")
        sns.set_theme(style="whitegrid")
        #Queue Performance
        st.subheader("1. Queue Performance & Customer Attrition Analysis")
        fig1 = plt.figure(figsize=(14, 5))
        plt.subplot(1, 2, 1)
        sns.boxplot(data=df_all[df_all['wait_time_mins'] > 0], x='Guest_type', y='wait_time_mins', palette='Set2')
        plt.title('1.1 Overall Wait Time (In-house vs Walk-in)')
        plt.ylabel('Wait Time (Minutes)')
        plt.subplot(1, 2, 2)
        walk_away_counts = df_all[df_all['walk_away'] == True]['Guest_type'].value_counts()
        if not walk_away_counts.empty:
            sns.barplot(x=walk_away_counts.index, y=walk_away_counts.values, palette='Reds')
        else:
            plt.text(0.5, 0.5, 'No Walk-aways', ha='center', va='center')
        plt.title('1.2 Overall Walk-aways by Guest Type')
        plt.ylabel('Total Walk-aways (Groups)')
        plt.tight_layout()
        st.pyplot(fig1)
        #Daily Guest Volume
        st.subheader("2. Daily Guest Volume & Peak Demand Analysis")
        fig2 = plt.figure(figsize=(10, 5))
        daily_pax = df_all.groupby(['Day', 'Guest_type'])['pax'].sum().reset_index()
        sns.barplot(data=daily_pax, x='Day', y='pax', hue='Guest_type', palette='viridis')
        plt.title('2. Total Guests (Pax) Comparison Across Days')
        plt.ylabel('Total Guests (Pax)')
        plt.xlabel('Day (Sheet Name)')
        st.pyplot(fig2)
        #Meal Duration
        st.subheader("3. Meal Duration & Table Occupancy Dynamics")
        df_meal = df_all[df_all['seated'] == True].copy()
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
        st.dataframe(df_all[df_all['seated'] == True].groupby('Guest_type')['meal_duration_mins'].mean().round(2))
    with tab2:
        # --- 1. เตรียมข้อมูล (Data Prep) ---
        # แปลงเวลา
        df_all['meal_start_dt'] = pd.to_datetime(df_all['meal_start_str'], format='%H:%M:%S', errors='coerce')
        df_all['meal_end_dt'] = pd.to_datetime(df_all['meal_end_str'], format='%H:%M:%S', errors='coerce')
        # คำนวณระยะเวลาทานจริง (Actual Duration)
        df_all['actual_duration_mins'] = (df_all['meal_end_dt'] - df_all['meal_start_dt']).dt.total_seconds() / 60
        df_seated = df_all.dropna(subset=['actual_duration_mins']).copy()
        # --- 2. คำนวณสถิติตามที่คุณวิเคราะห์ ---
        median_duration = df_seated['actual_duration_mins'].median()
        pct_under_120 = (df_seated['actual_duration_mins'] <= 120).mean() * 100
        pct_under_180 = (df_seated['actual_duration_mins'] <= 180).mean() * 100
        st.header("ทำไมการลดเวลา (Cap Seating Time) ถึงไม่เวิร์ก?")
        st.markdown("การจำกัดเวลาจาก 5 ชั่วโมง เหลือ 2-3 ชั่วโมง **ไม่กระทบพฤติกรรมจริงของลูกค้า** และไม่ได้ช่วยแก้ปัญหาช่วงคิวพีก")
        # แสดง Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Median เวลากินจริง", f"{median_duration:.0f} นาที")
        col2.metric("กินจบภายใน 120 นาที", f"{pct_under_120:.1f}%")
        col3.metric("กินจบภายใน 180 นาที", f"{pct_under_180:.1f}%")
        st.divider()
        # --- 3. กราฟที่ 1: การกระจายตัวของเวลา (Histogram + Cumulative) ---
        st.subheader("1. ลูกค้าส่วนใหญ่ใช้เวลาทานเท่าไหร่?")
        fig1 = px.histogram(
            df_seated, 
            x="actual_duration_mins", 
            nbins=40,
            title="การกระจายตัวของเวลานั่งทานจริง (Meal Duration)",
            labels={'actual_duration_mins': 'ระยะเวลาที่นั่งทาน (นาที)', 'count': 'จำนวนโต๊ะ'},
            color_discrete_sequence=['#1f77b4']
        )
        # เพิ่มเส้น 120 นาที
        fig1.add_vline(x=120, line_width=3, line_dash="dash", line_color="red", 
                      annotation_text=" Cap 120 นาที (กระทบลูกค้าน้อยมาก)", annotation_position="top right")
        st.plotly_chart(fig1, use_container_width=True)
        st.divider()
        # --- 4. กราฟที่ 2: Simulation จำลองการตัดเวลาช่วง Peak (Arrival Bunching) ---
        st.subheader("2. จำลองสถานการณ์: ถ้าบังคับออกตอน 120 นาที โต๊ะจะว่างขึ้นไหม?")
        st.markdown("เราจะจำลองยอดการใช้โต๊ะรายนาที (Minute-by-minute) โดยเปรียบเทียบเวลาทานจริง กับ กรณีที่เราบังคับให้ลูกค้าลุกเมื่อครบ 120 นาที")
        # สร้างฟังก์ชันคำนวณโต๊ะที่มีคนนั่งในแต่ละนาที
        def get_active_tables(df, end_col):
            # สร้างช่วงเวลาตั้งแต่ 06:00 ถึง 12:00
            time_range = pd.date_range("1900-01-01 06:00:00", "1900-01-01 12:00:00", freq="1min")
            active_counts = []
            
            for t in time_range:
                # นับจำนวนโต๊ะที่ meal_start <= t และ สิ้นสุด > t
                count = ((df['meal_start_dt'] <= t) & (df[end_col] > t)).sum()
                active_counts.append(count)
                
            return pd.DataFrame({'Time': time_range.time, 'Active_Tables': active_counts})
        # คำนวณเวลาสิ้นสุดจำลอง (Simulated End Time) ถ้า Cap ที่ 120 นาที
        # ถ้าเกิน 120 ให้ตัดจบที่ 120, ถ้าไม่เกิน ให้ใช้เวลาเดิม
        df_seated['simulated_end_120'] = df_seated.apply(
            lambda row: row['meal_start_dt'] + pd.Timedelta(minutes=120) 
            if row['actual_duration_mins'] > 120 
            else row['meal_end_dt'], 
            axis=1
        )
        # ดึงข้อมูลมาพล็อตกราฟ
        df_actual_active = get_active_tables(df_seated, 'meal_end_dt')
        df_simulated_active = get_active_tables(df_seated, 'simulated_end_120')
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_actual_active['Time'], y=df_actual_active['Active_Tables'], 
                                  mode='lines', name='ยอดใช้โต๊ะจากเวลาจริง', line=dict(color='blue', width=3)))
        fig2.add_trace(go.Scatter(x=df_simulated_active['Time'], y=df_simulated_active['Active_Tables'], 
                                  mode='lines', name='จำลอง Cap ที่ 120 นาที', line=dict(color='red', width=3, dash='dash')))
        fig2.update_layout(
            title="เปรียบเทียบยอดการใช้โต๊ะ (Actual vs 120-min Cap Simulation)",
            xaxis_title="เวลา (Time)",
            yaxis_title="จำนวนโต๊ะที่มีคนนั่ง (Active Tables)",
            hovermode="x unified"
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.info("**ข้อสรุป (Insights):** ปัญหาแท้จริงคือ **Arrival Bunching** (คนแห่มาพร้อมกัน) กราฟแสดงให้เห็นชัดเจนว่าในช่วงพีก (เช่น 08:00 - 09:30) เส้นสีแดงและสีน้ำเงินทับกันสนิท แปลว่าการ Cap เวลาที่ 120 นาที ไม่ได้ช่วยคืนพื้นที่โต๊ะในช่วงเวลาที่วิกฤตที่สุดเลย")
        st.header("แนวทางที่ 2: ขึ้นราคา 259 บาท 'ทุกวัน' เวิร์กไหม?")
        st.markdown("การขึ้นราคาแบบเหมารวม (Blanket Policy) **ไม่ใช่ทางแก้ที่ถูกต้อง** เพราะปัญหาคิวไม่ได้เกิดขึ้นตลอดเวลา การขึ้นราคาจะทำลายฐานลูกค้าในวันที่ร้านว่าง")
        # --- ตัวเลข Highlight ---
        col1, col2, col3 = st.columns(3)
        col1.metric("เวลาที่มีคิวเทียบกับเวลาทั้งหมด", "10.8%", "293 จาก 2,705 นาที", delta_color="off")
        col2.metric("จำนวนวันที่มีคิว", "2 จาก 5 วัน", "เฉพาะชีต 143, 153", delta_color="off")
        col3.metric("ช่วงเวลาคิวพีกสุด", "08:00 - 11:00", "หนักสุด 09:00-10:00", delta_color="off")
        st.divider()
        # --- กราฟ 1: ปัญหาไม่ได้เกิดทุกวัน (Bar Chart) ---
        st.subheader("1. ปัญหาคิวไม่ได้เกิดขึ้นทุกวัน")
        # จัดกลุ่มนับจำนวนคิว
        df_q = df_all.dropna(subset=['queue_start', 'queue_end']).copy()
        day_counts = df_q.groupby('Day').size().reset_index(name='Queue_Groups')
        all_days = pd.DataFrame({'Day': df_all['Day'].unique()})
        day_counts = pd.merge(all_days, day_counts, on='Day', how='left').fillna(0)
        # ทำสี Highlight เฉพาะวันที่มีคิว
        day_counts['Color'] = day_counts['Queue_Groups'].apply(lambda x: '#e74c3c' if x > 0 else '#d3d3d3')
        fig1 = go.Figure(data=[go.Bar(
            x=day_counts['Day'],
            y=day_counts['Queue_Groups'],
            marker_color=day_counts['Color'],
            text=day_counts['Queue_Groups'],
            textposition='auto'
        )])
        fig1.update_layout(title="จำนวนกลุ่มลูกค้าที่ต้องรอคิว แยกตามวัน (Sheet)", 
                           xaxis_title="วัน (Sheet)", yaxis_title="จำนวนกลุ่มที่รอคิว")
        st.plotly_chart(fig1, use_container_width=True)
        # --- กราฟ 2: ปัญหาไม่ได้เกิดทั้งวัน (Area Chart) ---
        st.subheader("2. ปัญหาคิวไม่ได้เกิดขึ้นทั้งวัน (กระจุกตัวช่วงสาย)")
        df_q['q_start_dt'] = pd.to_datetime('2026-01-01 ' + df_q['queue_start'].astype(str), errors='coerce').dt.tz_localize(None)
        df_q['q_end_dt'] = pd.to_datetime('2026-01-01 ' + df_q['queue_end'].astype(str), errors='coerce').dt.tz_localize(None)
        time_range = pd.date_range("2026-01-01 06:00:00", "2026-01-01 12:00:00", freq="1min")
        q_density = []
        for t in time_range:
            q_count = ((df_q['q_start_dt'].notna()) & (df_q['q_start_dt'] <= t) & (df_q['q_end_dt'].notna()) & (df_q['q_end_dt'] > t)).sum()
            q_density.append(q_count)
        fig2 = px.area(x=time_range, y=q_density, labels={'x': 'เวลา', 'y': 'จำนวนกลุ่มที่ยืนรอคิว'}, 
                       title="ความหนาแน่นของคิวรายนาที (รวมทุกวัน)")
        fig2.update_traces(line_color='#e74c3c', fillcolor='rgba(231, 76, 60, 0.4)')
        fig2.update_layout(xaxis_tickformat='%H:%M')
        # ตีกรอบช่วง 08:00 - 11:00
        fig2.add_vrect(x0="2026-01-01 08:00:00", x1="2026-01-01 11:00:00", 
                       fillcolor="yellow", opacity=0.2, layer="below", line_width=0,
                       annotation_text="Peak Period (08:00-11:00)", annotation_position="top left")
        st.plotly_chart(fig2, use_container_width=True)
        st.info("**ข้อสรุป (Insights):** หากจะใช้ราคาแก้ปัญหา ต้องเป็น **Targeted Pricing** เช่น การทำ Dynamic Pricing (Early Bird Discount) ให้ราคาถูกลงในช่วง 06:00-07:30 น. เพื่อจูงใจให้คนกระจายตัวออกมาจากช่วง Peak แทนที่จะขึ้นราคา 259 บาทเหมาทุกวัน ซึ่งจะทำให้เสียรายได้จาก Walk-in ในวันปกติไปฟรีๆ")

        st.header("แนวทางที่ 3: ให้สิทธิ์ In-house แซงคิว (Queue Skipping)")
        st.markdown("นโยบายนี้แก้ปัญหา **ผิดจุด** เพราะเป็นการจัดการความรู้สึก (Fairness) ไม่ใช่การเพิ่มขีดความสามารถในการรองรับ (Capacity) การลัดคิวจึงไม่มีประโยชน์ เพราะไม่มีโต๊ะว่างให้ไปนั่งอยู่ดี")

        # --- ตัวเลข Highlight จาก Insight ของคุณ ---
        col1, col2 = st.columns(2)
        col1.metric("คิวเฉลี่ยในช่วงที่มีคิว (Day 153)", "10.6 กลุ่ม", "Walk-in 7.8 | In-house 2.9", delta_color="off")
        col2.metric("โต๊ะที่ถูกใช้ ณ จุด Peak Queue", "24 ยูนิต", "Walk-in 18 | In-house 6", delta_color="off")

        st.divider()

        # --- Data Prep เฉพาะวัน 153 ---
        df_153 = df_all[df_all['Day'] == '153'].copy()
        df_153['Guest_type'] = df_153['Guest_type'].astype(str).str.strip().str.title()
        df_153['Guest_type'] = df_153['Guest_type'].replace({'Walk In': 'Walk-in', 'In House': 'In-house'})

        df_153['q_start'] = pd.to_datetime('2026-01-01 ' + df_153['queue_start'].astype(str), errors='coerce')
        df_153['q_end'] = pd.to_datetime('2026-01-01 ' + df_153['queue_end'].astype(str), errors='coerce')
        df_153['m_start'] = pd.to_datetime('2026-01-01 ' + df_153['meal_start'].astype(str), errors='coerce')
        df_153['m_end'] = pd.to_datetime('2026-01-01 ' + df_153['meal_end'].astype(str), errors='coerce')

        time_range = pd.date_range("2026-01-01 07:00:00", "2026-01-01 11:30:00", freq="1min")
        q_data, s_data = [], []

        for t in time_range:
            # คิว
            q_w = ((df_153['Guest_type'] == 'Walk-in') & (df_153['q_start'] <= t) & (df_153['q_end'] > t)).sum()
            q_i = ((df_153['Guest_type'] == 'In-house') & (df_153['q_start'] <= t) & (df_153['q_end'] > t)).sum()
            q_data.append({'Time': t, 'Walk-in': q_w, 'In-house': q_i})
            
            # นั่งโต๊ะ
            s_w = ((df_153['Guest_type'] == 'Walk-in') & (df_153['m_start'] <= t) & (df_153['m_end'] > t)).sum()
            s_i = ((df_153['Guest_type'] == 'In-house') & (df_153['m_start'] <= t) & (df_153['m_end'] > t)).sum()
            s_data.append({'Time': t, 'Walk-in': s_w, 'In-house': s_i})

        df_q_sim = pd.DataFrame(q_data)
        df_s_sim = pd.DataFrame(s_data)

        # --- กราฟ 1: Active Seating (เพื่อโชว์ Bottleneck) ---
        st.subheader("กราฟแสดงจำนวนโต๊ะที่ถูกใช้งาน (Table Occupancy) บนวัน 153")
        st.markdown("ณ จุดพีก โต๊ะถูกใช้งานเต็มความจุ (~24 ยูนิต) การแซงคิวจึงไม่มีประโยชน์ เพราะไม่มีโต๊ะว่างให้ไปนั่งอยู่ดี")

        fig_seat = go.Figure()
        fig_seat.add_trace(go.Scatter(x=df_s_sim['Time'], y=df_s_sim['In-house'], mode='lines', stackgroup='one', name='In-house (แขกโรงแรม)', fillcolor='#2ecc71', line=dict(color='#27ae60')))
        fig_seat.add_trace(go.Scatter(x=df_s_sim['Time'], y=df_s_sim['Walk-in'], mode='lines', stackgroup='one', name='Walk-in (ลูกค้าภายนอก)', fillcolor='#3498db', line=dict(color='#2980b9')))

        # เพิ่มเส้น Max Capacity แบบจำลอง
        fig_seat.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Max Capacity (~24 Tables)", annotation_position="top left")
        fig_seat.update_layout(xaxis_tickformat='%H:%M', yaxis_title="จำนวนโต๊ะที่กำลังใช้งาน", hovermode="x unified")
        st.plotly_chart(fig_seat, use_container_width=True)

        # --- ข้อสรุป ---
        st.error("""
        **บทสรุป (Key Takeaway):** Queue Skipping ไม่ใช่ 'Capacity Solution' แต่เป็นแค่การย้ายความเจ็บปวด (Pain) ไปรวมไว้ที่ Walk-in ซึ่งจะยิ่งดันให้ยอด Walk-away พุ่งสูงขึ้น นำไปสู่วิกฤตด้านรีวิวและภาพลักษณ์ของโรงแรม วิธีแก้ที่ถูกต้องคือการจัดการ **Table Management (รวม/แยกโต๊ะตาม Pax)** หรือจูงใจด้วยราคาเพื่อลด **Arrival Bunching** ครับ
        """)
else:
    st.info("💡 กรุณาอัปโหลดไฟล์ Excel Dataset ของคุณที่ด้านบนเพื่อเริ่มต้นใช้งานแดชบอร์ด")


