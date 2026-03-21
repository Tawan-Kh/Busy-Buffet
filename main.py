import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Busy Buffet Analytics", layout="wide")

st.title("🍽️ Busy Buffet - Data Analytics Dashboard")
st.markdown("แดชบอร์ดสรุปผลการวิเคราะห์ข้อมูลลูกค้า การรอคิว และระยะเวลาทานอาหาร")

# 1. สร้างช่องอัปโหลดไฟล์
uploaded_file = st.file_uploader("อัปโหลดไฟล์", type=['xlsx', 'csv'])

if uploaded_file is not None:
    try:
        # Load Data
        file_ext = uploaded_file.name.split('.')[-1].lower()
        if file_ext == 'csv':
            all_sheets = {'Sheet1': pd.read_csv(uploaded_file)}
        else:
            all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        cols = ['service_no.', 'pax', 'queue_start', 'queue_end', 'table_no.', 'meal_start', 'meal_end', 'Guest_type']
        dfs = []

        st.header("📊 Per-sheet Analytics (สรุปผลรายวัน)")
        
        # 2. จัดการทีละชีต และแสดงผลด้วย Metric ของ Streamlit
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

            total_pax = df_temp['pax'].sum()
            total_groups = len(df_temp)
            walk_aways = df_temp['walk_away'].sum()
            avg_wait = df_temp[df_temp['wait_time_mins'] > 0]['wait_time_mins'].mean()

            # แสดงผลแบบการ์ดตัวเลข (Metrics)
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

        # 3. รวม DataFrame และสร้างกราฟ
        if len(dfs) == 0:
            st.warning("ไม่พบข้อมูลที่สามารถใช้งานได้หลังจากกรองข้อมูลแล้ว กรุณาตรวจสอบคอลัมน์และประเภทข้อมูลในไฟล์ Excel")
            st.stop()

        df_all = pd.concat(dfs, ignore_index=True)
        st.header("📈 Queue Management & Customer Behavior Analytics")
        sns.set_theme(style="whitegrid")

        # กราฟ 1: Queue Performance
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

        # กราฟ 2: Daily Guest Volume
        st.subheader("2. Daily Guest Volume & Peak Demand Analysis")
        fig2 = plt.figure(figsize=(10, 5))
        daily_pax = df_all.groupby(['Day', 'Guest_type'])['pax'].sum().reset_index()
        sns.barplot(data=daily_pax, x='Day', y='pax', hue='Guest_type', palette='viridis')
        plt.title('2. Total Guests (Pax) Comparison Across Days')
        plt.ylabel('Total Guests (Pax)')
        plt.xlabel('Day (Sheet Name)')
        st.pyplot(fig2)

        # กราฟ 3: Meal Duration
        st.subheader("3. Meal Duration & Table Occupancy Dynamics")
        fig3 = plt.figure(figsize=(14, 5))
        plt.subplot(1, 2, 1)
        sns.histplot(data=df_all[df_all['seated'] == True], x='meal_duration_mins', hue='Guest_type', kde=True, bins=20, palette='Set1')
        plt.title('3.1 Meal Duration Distribution (All Days)')
        plt.xlabel('Meal Duration (Minutes)')

        plt.subplot(1, 2, 2)
        sns.boxplot(data=df_all[df_all['seated'] == True], x='Guest_type', y='meal_duration_mins', palette='Set1')
        plt.title('3.2 Meal Duration Spread (All Days)')
        plt.ylabel('Meal Duration (Minutes)')
        plt.tight_layout()
        st.pyplot(fig3)

        # สรุปภาพรวม
        st.header("📌 สถิติภาพรวม (Overall)")
        st.write("**ระยะเวลาทานอาหารเฉลี่ย (นาที) แยกตามประเภทลูกค้า:**")
        st.dataframe(df_all[df_all['seated'] == True].groupby('Guest_type')['meal_duration_mins'].mean().round(2))

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
else:
    st.info("💡 กรุณาอัปโหลดไฟล์ Excel Dataset ของคุณที่ด้านบนเพื่อเริ่มต้นใช้งานแดชบอร์ด")