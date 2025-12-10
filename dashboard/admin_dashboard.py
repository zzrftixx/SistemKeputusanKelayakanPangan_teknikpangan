import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Admin Dashboard - Lab Pangan", layout="wide", page_icon="📊")

st.title("📊 Dashboard Monitoring & Statistik")

# 1. Load Data
@st.cache_data(ttl=60) # Cache 1 menit biar update realtime
def load_data():
    access_log = None
    lab_log = None
    
    if os.path.exists("../csv/access_log.csv"):
        access_log = pd.read_csv("../csv/access_log.csv")
        access_log['timestamp'] = pd.to_datetime(access_log['timestamp'])
        
    if os.path.exists("../history_lab.csv"):
        lab_log = pd.read_csv("../history_lab.csv")
        lab_log['timestamp'] = pd.to_datetime(lab_log['timestamp'])
        
    return access_log, lab_log

df_access, df_lab = load_data()

# --- TABS ----
tab1, tab2 = st.tabs(["👥 Traffic & Pengunjung", "🧪 Analisis Laboratorium (Data Pangan)"])

# TAB 1: TRAFFIC
with tab1:
    if df_access is not None and not df_access.empty:
        # KPI Cards
        total_visits = len(df_access)
        unique_users = df_access['session_id'].nunique()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Kunjungan (Hits)", total_visits)
        col2.metric("User Unik (Estimasi)", unique_users)
        
        # Grafik Kunjungan per Waktu
        # Resample per Jam
        traffic_trend = df_access.set_index('timestamp').resample('H').count()
        
        st.subheader("Tren Kunjungan (Per Jam)")
        st.area_chart(traffic_trend['session_id'])
        
        # Tabel Log Terakhir
        with st.expander("Lihat Log Akses Mentah"):
            st.dataframe(df_access.sort_values('timestamp', ascending=False))
            
    else:
        st.warning("Belum ada data kunjungan. Buka Aplikasi Utama dulu untuk generate log.")

# TAB 2: LAB STATS
with tab2:
    if df_lab is not None and not df_lab.empty:
        st.header("Statistik Keamanan Pangan")
        
        # 1. Distribusi Aman vs Bahaya
        pie_data = df_lab['prediksi'].value_counts().reset_index()
        pie_data.columns = ['Status', 'Jumlah']
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Rasio Keamanan")
            fig_pie = px.pie(pie_data, values='Jumlah', names='Status', color='Status',
                             color_discrete_map={'AMAN DIMAKAN':'green', 'TIDAK AMAN / BERBAHAYA':'red'})
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            st.subheader("Rata-rata Risk Score per Kategori")
            risk_cat = df_lab.groupby('kategori')['risk_score'].mean().reset_index()
            fig_bar = px.bar(risk_cat, x='kategori', y='risk_score', color='risk_score',
                             color_continuous_scale='RdYlGn_r') # Merah tinggi = bahaya
            st.plotly_chart(fig_bar, use_container_width=True)
            
        # 2. Scatter Plot: Suhu vs Lama Simpan (Pewarnaan by Safe/Unsafe)
        st.subheader("Peta Persebaran Bahaya (Suhu vs Waktu)")
        fig_scatter = px.scatter(df_lab, x='lama_simpan', y='suhu', color='prediksi',
                                 hover_data=['bahan_baku'], symbol='kategori',
                                 title="Apakah Lama Simpan & Suhu Mempengaruhi Keamanan?")
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # 3. Word Cloud-ish (Frekuensi Bahan)
        st.subheader("Bahan Paling Sering Diuji")
        st.bar_chart(df_lab['bahan_baku'].value_counts().head(10))
        
    else:
        st.warning("Belum ada data laboratorium. Lakukan prediksi di aplikasi utama dulu.")
