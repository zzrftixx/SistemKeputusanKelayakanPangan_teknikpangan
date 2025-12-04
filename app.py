import streamlit as st
import pandas as pd
import joblib
import numpy as np
import google.generativeai as genai
import os
from datetime import datetime

st.set_page_config(page_title="Food Safety Lab", layout="wide")

# Sidebar untuk Konfigurasi AI
with st.sidebar:
    st.header("⚙️ Konfigurasi AI (Gemini)")
    # API Key dari user (Hardcoded sesuai request)
    # WARNING: Jangan push file ini ke public repo tanpa menghapus key ini!
    default_key = "AIzaSyAsxUN8radcvflnv4_2QsZKrEk69u1FZdA"
    
    # Kita set langsung ke google-generativeai
    genai.configure(api_key=default_key)
    
    # Tampilkan status (masked)
    st.success(f"API Key Terpasang: {default_key[:5]}...{default_key[-4:]}")
    st.info("Mode: Super Informative AI (Gemini)")
    
    st.divider()
    st.header("📂 Data Laboratorium")
    if os.path.exists("history_lab.csv"):
        df_log = pd.read_csv("history_lab.csv")
        st.write(f"Total Sampel: {len(df_log)}")
        st.download_button(
            label="Download Log Lab (CSV)",
            data=df_log.to_csv(index=False),
            file_name="history_lab.csv",
            mime="text/csv"
        )   

st.title("Pendeteksi Kelayakan Makanan")

st.write("Isi karakteristik makanan lalu klik prediksi.")

# Load model pipeline (sudah termasuk preprocessor)
model = joblib.load("model.pkl")

# Layout 2 Kolom
col1, col2 = st.columns(2)

with col1:
    st.subheader("Karakteristik Fisik")
    # Ambil opsi unik dari dataset untuk dropdown (hardcoded sementara agar cepat)
    kategori = st.selectbox("Kategori Pangan:", ["Daging", "Sayur", "Nasi", "Susu", "Roti", "Gorengan", "Buah", "Telur", "Minuman"])
    bahan = st.text_input("Nama Bahan (Contoh: Ayam mentah):", "Ayam mentah")
    warna = st.selectbox("Warna:", ["merah muda", "merah segar", "coklat kehijauan", "biru lebam", "perak cerah", "mata cekung kusam", "hijau segar", "hijau kecoklatan", "oranye cerah", "merah berair", "putih bersih", "putih kekuningan", "berjamur oranye", "kekuningan aneh", "putih kental", "coklat keemasan", "coklat gelap", "berminyak parah", "warna alami", "hitam legam", "cerah", "kusam", "oranye", "berbuih"])
    bau = st.selectbox("Bau:", ["normal", "busuk tajam", "segar", "amis menyengat", "busuk", "apek", "tanah segar", "asam menyengat", "wangi pandan", "agak asam", "tengik", "creamy", "asam kuat", "asam segar", "ragi harum", "jamur tajam", "gurih", "manis segar", "alkohol", "sedikit amis", "jeruk segar", "fermentasi"])
    tekstur = st.selectbox("Tekstur:", ["kenyal", "licin berlendir", "lembek", "kenyal licin", "hancur", "renyah", "layu berlendir", "keras", "lembek hancur", "pulen", "menggumpal", "kental halus", "empuk", "alot", "padat juicy", "lembek berair", "padat", "retak", "cair"])

with col2:
    st.subheader("Kondisi Penyimpanan")
    suhu = st.slider("Suhu Penyimpanan (°C):", -10, 100, 25)
    lama_simpan = st.number_input("Lama Simpan (Jam):", min_value=0, value=1)
    ph = st.slider("Perkiraan pH (Keasaman):", 0.0, 14.0, 7.0)

# --- LOGIC FUNCTIONS (PHASE 2) ---

def get_recommendation(kategori, suhu, prediction_label):
    if prediction_label == "TIDAK AMAN / BERBAHAYA":
        return "⛔ **TINDAKAN:** Segera pisahkan dan buang. Jangan berikan ke hewan ternak. Bersihkan area penyimpanan."
    
    # Jika Aman
    rec = "✅ **SARAN:** "
    if kategori in ["Daging", "Ikan"]:
        if suhu > 4:
            rec += "Segera masak atau simpan di freezer (-18°C) jika tidak langsung diolah."
        else:
            rec += "Pertahankan suhu dingin. Masak hingga matang sempurna (min 75°C)."
    elif kategori in ["Sayur", "Buah"]:
        rec += "Cuci bersih dengan air mengalir. Simpan di suhu sejuk (10-15°C) atau kulkas."
    elif kategori == "Susu":
        rec += "Pastikan wadah tertutup rapat. Simpan di suhu < 4°C."
    elif kategori == "Nasi":
        rec += "Segera habiskan. Jangan simpan di suhu ruang > 4 jam (risiko B. cereus)."
    else:
        rec += "Simpan di tempat kering dan sejuk. Cek tanggal kadaluarsa."
    return rec

def estimate_shelf_life(kategori, suhu, lama_simpan_sekarang):
    # Heuristik sederhana (Estimasi kasar)
    base_hours = 24 # Default
    
    if kategori in ["Daging", "Ikan", "Susu"]:
        if suhu < 0: base_hours = 720 # 1 bulan (beku)
        elif suhu < 5: base_hours = 48 # 2 hari (kulkas)
        else: base_hours = 4 # 4 jam (suhu ruang)
    elif kategori in ["Sayur", "Buah"]:
        if suhu < 15: base_hours = 168 # 1 minggu
        else: base_hours = 48 # 2 hari
    elif kategori == "Nasi":
        if suhu > 60: base_hours = 12 # Warmer
        elif suhu < 5: base_hours = 24 
        else: base_hours = 6 # Suhu ruang bahaya
        
    sisa = base_hours - lama_simpan_sekarang
    if sisa < 0: return "0 jam (Sudah lewat batas aman)"
    return f"{sisa} jam lagi (Estimasi pada suhu {suhu}°C)"

def log_to_csv(data_dict, prediction, risk_score):
    file_name = "history_lab.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_data = {
        "timestamp": timestamp,
        **data_dict,
        "prediksi": prediction,
        "risk_score": risk_score
    }
    
    df_new = pd.DataFrame([log_data])
    
    if not os.path.exists(file_name):
        df_new.to_csv(file_name, index=False)
    else:
        df_new.to_csv(file_name, mode='a', header=False, index=False)

# --- END LOGIC FUNCTIONS ---

# Fungsi Penjelasan Offline (Rule-Based)
def generate_offline_explanation(data_dict, prediction_label, risk_score, error_msg=""):
    reasons = []
    recommendations = []
    
    # Analisis Suhu
    if data_dict['suhu'] > 40:
        reasons.append(f"Suhu penyimpanan ekstrem ({data_dict['suhu']}°C) mempercepat denaturasi protein dan pertumbuhan bakteri termofilik.")
        recommendations.append("Jangan konsumsi. Risiko keracunan tinggi.")
    elif data_dict['suhu'] > 5 and data_dict['lama_simpan'] > 4:
        reasons.append(f"Suhu 'Danger Zone' ({data_dict['suhu']}°C) selama >4 jam memungkinkan bakteri membelah diri secara eksponensial.")
    
    # Analisis Waktu
    if data_dict['lama_simpan'] > 24 and "segar" in data_dict['bahan_baku'].lower():
        reasons.append(f"Penyimpanan {data_dict['lama_simpan']} jam untuk bahan segar tanpa pembekuan menurunkan kualitas drastis.")
    
    # Analisis pH
    if data_dict['ph'] < 4.6:
        reasons.append("pH rendah (asam). Jika bukan makanan fermentasi, ini indikasi pembusukan asam (souring).")
    elif data_dict['ph'] > 7.5:
        reasons.append("pH basa tinggi. Indikasi pemecahan protein menjadi amonia (pembusukan lanjut).")

    # Analisis Fisik
    if "busuk" in data_dict['bau'].lower() or "amis" in data_dict['bau'].lower():
        reasons.append("Bau menyimpang (off-odor) adalah tanda pasti aktivitas mikroba pembusuk.")
    if "lendir" in data_dict['tekstur'].lower():
        reasons.append("Tekstur berlendir menandakan pembentukan biofilm bakteri di permukaan.")

    # Jika Aman
    if prediction_label == "AMAN DIMAKAN" and not reasons:
        reasons.append("Parameter suhu, waktu, dan fisik berada dalam batas wajar untuk kategori ini.")
        recommendations.append("Pastikan dimasak dengan benar sebelum dikonsumsi.")

    reason_text = " ".join(reasons) if reasons else "Kombinasi parameter memerlukan pengecekan lab lebih lanjut."
    rec_text = " ".join(recommendations) if recommendations else "Lakukan uji organoleptik (bau/rasa) sebelum konsumsi."

    error_display = f"\n\n**⚠️ ERROR API:** {error_msg}" if error_msg else ""

    return f"""
    ### ⚠️ Mode Offline (AI Tidak Terhubung)
    
    **Analisis Sistem:**
    *   **Status**: {prediction_label}
    *   **Deteksi Anomali**: {reason_text}
    *   **Saran**: {rec_text}
    
    *Catatan: Terjadi masalah saat menghubungi AI. Sistem menggunakan logika offline.*
    {error_display}
    """

# Fungsi Penjelasan AI (Gemini)
def generate_explanation(data_dict, prediction_label, risk_score):
    # API Key sudah di-set di awal (hardcoded)
    
    prompt = f"""
    Kamu adalah Profesor Ahli Mikrobiologi dan Keamanan Pangan (Food Safety Scientist) dengan pengalaman 30 tahun.
    Tugasmu adalah memberikan LAPORAN FORENSIK LENGKAP mengenai sampel makanan ini. Jangan pelit informasi.

    DATA SAMPEL:
    - Kategori: {data_dict['kategori']}
    - Bahan: {data_dict['bahan_baku']}
    - Ciri Fisik: Warna {data_dict['warna']}, Bau {data_dict['bau']}, Tekstur {data_dict['tekstur']}
    - Parameter Lingkungan: Suhu {data_dict['suhu']}°C, Waktu {data_dict['lama_simpan']} jam, pH {data_dict['ph']}

    HASIL LAB:
    - Prediksi: {prediction_label}
    - Tingkat Risiko: {risk_score:.1f}%

    BUATLAH LAPORAN DENGAN STRUKTUR BERIKUT (Gunakan Bahasa Indonesia Formal & Ilmiah):

    ### 1. 🔬 Analisis Biokimia & Fisik (Deep Dive)
    Jelaskan secara mendalam apa yang terjadi pada level molekuler. 
    - Hubungkan suhu {data_dict['suhu']}°C dengan kinetika reaksi pembusukan.
    - Hubungkan pH {data_dict['ph']} dengan stabilitas mikroba.
    - Jelaskan mengapa tekstur '{data_dict['tekstur']}' dan bau '{data_dict['bau']}' muncul (misal: proteolisis, lipolisis, fermentasi).

    ### 2. 🦠 Identifikasi Bahaya Mikrobiologis
    Sebutkan minimal 3 patogen spesifik yang SANGAT MUNGKIN tumbuh di {data_dict['kategori']} pada kondisi ini.
    - Contoh: Salmonella, E. coli O157:H7, Listeria monocytogenes, Clostridium botulinum, Staphylococcus aureus, Bacillus cereus, Aspergillus flavus.
    - Jelaskan dampak kesehatan jika tertelan (misal: neurotoksin, infeksi gastrointestinal).

    ### 3. 🛡️ Protokol Penanganan & Mitigasi
    Berikan instruksi teknis yang sangat spesifik.
    - Jika AMAN: Bagaimana cara memperpanjang umur simpannya? (Suhu ideal, jenis wadah).
    - Jika BAHAYA: Bagaimana prosedur pembuangan yang aman agar spora tidak menyebar? Apakah pemanasan bisa membunuh racunnya?

    ### 4. 📊 Kesimpulan Profesor
    Satu kalimat penutup yang tegas mengenai status kelayakan konsumsi.

    Panjang jawaban minimal 300 kata. Berikan fakta ilmiah yang jarang diketahui orang awam.
    """

    # Daftar model yang akan dicoba (Fallback mechanism)
    models_to_try = [
        'gemini-2.0-flash',       # Standard Flash (Cepat & Stabil)
        'gemini-2.0-flash-lite',  # Lite version
        'gemini-2.5-flash',       # Newer version
        'gemini-flash-latest'     # Alias for latest stable
    ]

    last_error = ""

    for model_name in models_to_try:
        try:
            # Konfigurasi Model Gemini
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                continue # Coba model berikutnya jika limit habis
            else:
                # Jika error lain (misal 404), mungkin model tidak ada, lanjut coba yang lain
                continue
    
    # Jika semua gagal
    return generate_offline_explanation(data_dict, prediction_label, risk_score, error_msg=f"Semua model sibuk/gagal. Terakhir: {last_error}")

# Tombol Prediksi
if st.button("Cek Keamanan Pangan"):
    # Buat dataframe untuk input (sesuai format training)
    input_data = pd.DataFrame({
        "kategori": [kategori],
        "bahan_baku": [bahan],
        "warna": [warna],
        "bau": [bau],
        "tekstur": [tekstur],
        "suhu": [suhu],
        "lama_simpan": [lama_simpan],
        "ph": [ph]
    })

    # Prediksi
    prediction = model.predict(input_data)[0]
    probability = model.predict_proba(input_data)[0][1] # Ambil probabilitas kelas 1 (Aman)
    risk_score = (1 - probability) * 100 # Risk score adalah kebalikan dari aman

    # --- LOGGING (PHASE 2) ---
    pred_label = "AMAN DIMAKAN" if prediction == 1 else "TIDAK AMAN / BERBAHAYA"
    
    # Prepare data dict
    data_dict = {
        "kategori": kategori,
        "bahan_baku": bahan,
        "warna": warna,
        "bau": bau,
        "tekstur": tekstur,
        "suhu": suhu,
        "lama_simpan": lama_simpan,
        "ph": ph
    }
    
    # Save to CSV
    log_to_csv(data_dict, pred_label, risk_score)
    st.toast("Data berhasil disimpan ke Log Lab!", icon="💾")
    # -------------------------

    st.divider()
    st.subheader("Hasil Analisis Laboratorium")

    col_res1, col_res2 = st.columns(2)

    with col_res1:
        if prediction == 1:
            st.success(f"✅ STATUS: {pred_label}")
        else:
            st.error(f"⚠️ STATUS: {pred_label}")
        
        # Tampilkan Saran & Shelf Life (PHASE 2)
        st.info(get_recommendation(kategori, suhu, pred_label))
        st.write(f"**Estimasi Sisa Umur Simpan:** {estimate_shelf_life(kategori, suhu, lama_simpan)}")

    with col_res2:
        st.metric(label="Risk Score (Tingkat Risiko)", value=f"{risk_score:.1f}%")
        if risk_score < 20:
            st.caption("Risiko rendah. Makanan dalam kondisi prima.")
        elif risk_score < 50:
            st.caption("Risiko sedang. Perhatikan tanda-tanda fisik.")
        else:
            st.caption("Risiko TINGGI. Jangan dikonsumsi!")
    
    # AI Explanation Section
    st.divider()
    st.subheader("🤖 Penjelasan Ahli AI (Super Detail)")
    with st.spinner("Profesor sedang menganalisis sampel di mikroskop..."):
        explanation = generate_explanation(data_dict, pred_label, risk_score)
        st.markdown(explanation)
