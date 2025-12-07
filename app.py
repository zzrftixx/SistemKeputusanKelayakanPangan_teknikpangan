import streamlit as st
import pandas as pd
import joblib
import numpy as np
import google.generativeai as genai
import os
import time
from datetime import datetime

st.set_page_config(page_title="Food Safety Lab", layout="wide")

# Sidebar untuk Konfigurasi AI
with st.sidebar:
    st.header("⚙️ Konfigurasi AI (Gemini)")
    
    # Logika Keamanan API Key (Anti-Intip)
    api_key = None
    using_secrets = False

    # 1. Coba load dari Secrets (Server-side only)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            using_secrets = True
            st.success("✅ API Key terdeteksi dari Secrets (Aman & Tersembunyi).")
        else:
            # Fallback: Coba baca manual file toml (jika Streamlit belum reload secrets)
            import toml
            secrets_path = ".streamlit/secrets.toml"
            if os.path.exists(secrets_path):
                with open(secrets_path, "r") as f:
                    secrets = toml.load(f)
                    if "GEMINI_API_KEY" in secrets:
                        api_key = secrets["GEMINI_API_KEY"]
                        using_secrets = True
                        st.success("✅ API Key terdeteksi (Manual Load).")
    except Exception as e:
        st.warning(f"Gagal load secrets: {e}")

    # 2. Opsi Timpa/Input Manual
    # Value dikosongkan agar key asli tidak terekspos di frontend (Inspect Element)
    manual_key = st.text_input("Ganti/Isi API Key (Opsional)", type="password", help="Isi ini HANYA jika ingin menggunakan key yang berbeda dari Secrets.")

    # 3. Penentuan Key Final
    if manual_key:
        api_key = manual_key
        st.info("Menggunakan API Key manual.")
    elif not api_key:
        st.warning("⚠️ Mode Offline: API Key belum diset.")

    # 4. Konfigurasi
    if api_key:
        genai.configure(api_key=api_key)
    
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

st.title("Pendeteksi Kelayakan Pangan")

# --- PANDUAN PENGGUNAAN ---
with st.expander("📖 Panduan Penggunaan Aplikasi (Klik Disini)"):
    st.markdown("""
    **Selamat Datang di Laboratorium Digital!** 🔬
    Aplikasi ini membantu kamu menilai apakah makanan aman dimakan atau tidak.
    
    **Cara Pakai:**
    1.  **Isi Data Fisik**: Pilih Kategori, Bahan, Warna, Bau, dan Tekstur.
        *   *Tips: Kalau pilihan tidak ada, pilih "Lainnya (Isi Sendiri)" lalu ketik manual.*
    2.  **Isi Kondisi Penyimpanan**:
        *   **Suhu**: Perkirakan suhu tempat makanan disimpan.
        *   **Waktu**: Pilih satuan (Jam/Hari) dan masukkan angkanya.
        *   **pH**: Otomatis terisi, tapi bisa digeser jika kamu punya alat ukur pH.
    3.  **Klik Prediksi**: Tunggu sebentar, Profesor AI akan menganalisisnya!
    """)

st.write("Isi karakteristik makanan lalu klik prediksi.")

# Load model pipeline (sudah termasuk preprocessor)
model = joblib.load("model.pkl")

# Load Dataset untuk Dropdown Dinamis & Auto-pH
try:
    df_pangan = pd.read_csv("dataset_pangan.csv")
    # 1. Database Bahan per Kategori
    food_db = df_pangan.groupby('kategori')['bahan_baku'].unique().apply(list).to_dict()
    # 2. Database Rata-rata pH per Bahan
    ph_db = df_pangan.groupby('bahan_baku')['ph'].mean().to_dict()
    categories = sorted(list(food_db.keys()))
except Exception as e:
    st.error(f"Gagal memuat dataset: {e}")
    categories = ["Daging", "Sayur", "Buah"] # Fallback
    food_db = {}
    ph_db = {}

# Helper Function untuk Input Custom
def render_custom_input(label, options, key_suffix):
    # Tambahkan opsi "Lainnya"
    options_with_custom = list(options) + ["Lainnya (Isi Sendiri)"]
    selected = st.selectbox(label, options_with_custom, key=f"select_{key_suffix}")
    
    if selected == "Lainnya (Isi Sendiri)":
        return st.text_input(f"Masukkan {label} Manual:", key=f"text_{key_suffix}")
    return selected

# Helper Function untuk AI pH
def get_ai_estimated_ph(bahan_nama):
    models_to_try = [
        'gemini-2.0-flash-lite',      # Prioritas 1: Lite (Cepat & Hemat)
        'gemini-2.0-flash',           # Prioritas 2: Standard
        'gemini-flash-latest',        # Fallback 1: Latest Stable
        'gemini-pro'                  # Fallback 2: Old Reliable
    ]
    last_error = "Unknown Error"
    
    for model_name in models_to_try:
        try:
            model_ph = genai.GenerativeModel(model_name)
            prompt_ph = f"""
            Berapa rata-rata pH dari '{bahan_nama}'? 
            Jawab HANYA angka satu desimal (contoh: 5.5). 
            Jika ada rentang (misal 5-6), ambil nilai tengahnya.
            Jangan ada teks lain.
            """
            
            # Retry Logic
            for attempt in range(3):
                try:
                    response = model_ph.generate_content(prompt_ph)
                    text = response.text.strip()
                    
                    # Coba parsing angka langsung
                    import re
                    # Cari angka float pertama (5.5 atau 5)
                    match = re.search(r"[-+]?\d*\.\d+|\d+", text)
                    if match:
                        return float(match.group()), None # Success, No Error
                    
                except Exception as e:
                    last_error = str(e)
                    if "429" in str(e):
                        time.sleep(2 * (attempt + 1)) # Backoff
                        continue
                    else:
                        print(f"Error AI pH (Attempt {attempt}): {e}")
                        # Don't break immediately, try retry
            
        except Exception as e:
            last_error = str(e)
            continue

    return None, last_error # Return None and the last error message

# Layout 2 Kolom
col1, col2 = st.columns(2)
with col1:
    st.subheader("Karakteristik Fisik")
    
    # 1. Kategori (Dinamis + Custom)
    kategori = render_custom_input("Kategori Pangan:", categories, "kategori")
    
    # 2. Bahan (Filter berdasarkan Kategori + Custom)
    # Jika kategori custom (tidak ada di db), opsi bahan kosong -> user harus isi manual
    bahan_options = food_db.get(kategori, [])
    if not bahan_options:
        bahan_options = ["Lainnya (Isi Sendiri)"] # Default jika kategori baru
        
    bahan = render_custom_input("Nama Bahan:", bahan_options, "bahan")
    
    # 3. Warna & Bau & Tekstur (Custom)
    warna_opts = ["merah muda", "merah segar", "coklat kehijauan", "biru lebam", "perak cerah", "mata cekung kusam", "hijau segar", "hijau kecoklatan", "oranye cerah", "merah berair", "putih bersih", "putih kekuningan", "berjamur oranye", "kekuningan aneh", "putih kental", "coklat keemasan", "coklat gelap", "berminyak parah", "warna alami", "hitam legam", "cerah", "kusam", "oranye", "berbuih"]
    warna = render_custom_input("Warna:", warna_opts, "warna")
    
    bau_opts = ["normal", "busuk tajam", "segar", "amis menyengat", "busuk", "apek", "tanah segar", "asam menyengat", "wangi pandan", "agak asam", "tengik", "creamy", "asam kuat", "asam segar", "ragi harum", "jamur tajam", "gurih", "manis segar", "alkohol", "sedikit amis", "jeruk segar", "fermentasi"]
    bau = render_custom_input("Bau:", bau_opts, "bau")
    
    tekstur_opts = ["kenyal", "licin berlendir", "lembek", "kenyal licin", "hancur", "renyah", "layu berlendir", "keras", "lembek hancur", "pulen", "menggumpal", "kental halus", "empuk", "alot", "padat juicy", "lembek berair", "padat", "retak", "cair"]
    tekstur = render_custom_input("Tekstur:", tekstur_opts, "tekstur")

with col2:
    st.subheader("Kondisi Penyimpanan")
    
    # 4. Suhu
    suhu = st.slider("Suhu Penyimpanan (°C):", -10, 100, 25)
    
    # 5. Lama Simpan (Jam/Hari)
    col_waktu1, col_waktu2 = st.columns([1, 2])
    with col_waktu1:
        satuan_waktu = st.radio("Satuan:", ["Jam", "Hari"])
    with col_waktu2:
        waktu_input = st.number_input(f"Lama Simpan ({satuan_waktu}):", min_value=0, value=1)
    
    # Konversi ke Jam untuk sistem
    lama_simpan = waktu_input * 24 if satuan_waktu == "Hari" else waktu_input
    
    # 6. pH (Auto-Adjust Logic with AI)
    # Initialize session state jika belum ada
    if 'ph_val' not in st.session_state:
        st.session_state['ph_val'] = 7.0
        
    # Jika user ganti bahan, update default pH dari database (Hanya jika bukan 'Lainnya')
    # Kita pakai database lokal dulu biar cepat, AI by call button
    if bahan in ph_db and bahan != "Lainnya (Isi Sendiri)":
         # Hanya update jika nilai belum diset manual atau tombol ditekan (logic agak tricky, simpler: update on change bahan)
         # Karena Streamlit rerun, kita perlu logic sederhana:
         # Kita biarkan slider pakai key session state, kita update session state kalau perlu.
         pass # Biarkan user/AI yang set

    # UI Bundle: Info + Button (Aesthetic Layout)
    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.info("ℹ️ **Info pH:** Klik tombol disamping untuk minta AI menebak nilai pH.", icon="🧪")
    with col_btn:
        st.write("") # Spacer vertical alignment
        if st.button("✨ Tanya Ph Pakai AI", use_container_width=True, help="AI akan menebak pH berdasarkan nama bahan."):
            with st.spinner("⏳ Mengukur pH..."):
                ai_ph, error_msg = get_ai_estimated_ph(bahan)
                if ai_ph:
                    st.session_state['ph_val'] = ai_ph
                    st.toast(f"pH {bahan}: {ai_ph}", icon="✅")
                else:
                    st.error(f"Gagal estimasi: {error_msg}")

    # Slider Full Width
    ph = st.slider("Perkiraan pH (Keasaman):", 0.0, 14.0, key="ph_val", help="Nilai ini estimasi. Geser jika punya alat ukur.")

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

# Fungsi Penjelasan Offline (Rule-Based & Enhanced UI)
def generate_offline_explanation(data_dict, prediction_label, risk_score, error_msg=""):
    reasons = []
    recommendations = []
    
    # --- LOGIKA PAKAR (Rule-Based) ---
    # 1. Analisis Suhu
    if data_dict['suhu'] > 40:
        reasons.append(f"🔥 **Bahaya Suhu Tinggi**: Penyimpanan pada {data_dict['suhu']}°C memicu pertumbuhan bakteri termofilik dan denaturasi protein.")
        recommendations.append("⛔ **Tindakan**: Jangan dikonsumsi! Risiko keracunan makanan sangat tinggi.")
    elif data_dict['suhu'] > 5 and data_dict['lama_simpan'] > 4:
        reasons.append(f"⚠️ **Danger Zone**: Makanan berada di suhu kritis ({data_dict['suhu']}°C) selama >4 jam. Bakteri membelah diri setiap 20 menit.")
        recommendations.append("⚠️ **Saran**: Jika belum berbau/berlendir, panaskan hingga mendidih (100°C) sebelum dimakan. Jika ragu, buang.")
    
    # 2. Analisis Waktu
    if data_dict['lama_simpan'] > 24 and "segar" in data_dict['bahan_baku'].lower():
        reasons.append(f"⏳ **Kedaluwarsa**: Penyimpanan {data_dict['lama_simpan']} jam untuk bahan segar tanpa pembekuan menurunkan kualitas nutrisi secara drastis.")
    
    # 3. Analisis pH
    if data_dict['ph'] < 4.6:
        reasons.append("🧪 **Keasaman Tinggi**: pH rendah (<4.6) mengindikasikan fermentasi asam atau pembusukan (souring).")
    elif data_dict['ph'] > 7.5:
        reasons.append("🧪 **Kebasaan Tinggi**: pH basa (>7.5) adalah tanda pemecahan protein menjadi amonia (pembusukan lanjut).")

    # 4. Analisis Fisik
    if "busuk" in data_dict['bau'].lower() or "amis" in data_dict['bau'].lower():
        reasons.append("🤢 **Indikator Bau**: Terdeteksi bau menyimpang (off-odor) akibat aktivitas mikroba pembusuk.")
    if "lendir" in data_dict['tekstur'].lower():
        reasons.append("🦠 **Biofilm Bakteri**: Tekstur berlendir menandakan koloni bakteri telah membentuk lapisan pelindung di permukaan.")

    # Jika Aman (Default)
    if prediction_label == "AMAN DIMAKAN" and not reasons:
        reasons.append("✅ **Parameter Normal**: Suhu, waktu, dan ciri fisik berada dalam batas aman standar keamanan pangan.")
        recommendations.append("🍽️ **Saran**: Aman dikonsumsi. Pastikan dimasak dengan benar (min 75°C) untuk keamanan ekstra.")

    # Gabungkan text
    reason_text = "\n\n".join(reasons) if reasons else "🔍 Kombinasi parameter memerlukan pengecekan lab lebih lanjut."
    rec_text = "\n\n".join(recommendations) if recommendations else "👀 Lakukan uji organoleptik (bau/rasa/lihat) sebelum konsumsi."

    error_display = f"""
    <div style="background-color: #ffebee; padding: 10px; border-radius: 5px; margin-top: 10px; border: 1px solid #ffcdd2;">
        <small>⚠️ <b>Sistem AI Offline:</b> {error_msg}</small>
    </div>
    """ if error_msg else ""

    # Return Markdown yang Cantik
    return f"""
    ### 🧬 Analisis Laboratorium (Mode Offline)
    
    **Status Sampel:** `{prediction_label}`
    
    #### 🔍 Deteksi Anomali & Fakta Ilmiah:
    {reason_text}
    
    #### 🛡️ Rekomendasi Tindakan:
    {rec_text}
    
    ---
    {error_display}
    """

# Fungsi Penjelasan AI (Gemini)
def generate_explanation(data_dict, prediction_label, risk_score):
    # API Key sudah di-set di awal (hardcoded)
    
    prompt = f"""
    Kamu adalah PROFESOR AUDITOR untuk sistem keamanan pangan berbasis Machine Learning.
    
    TUGAS UTAMA:
    1. VALIDASI hasil prediksi mesin.
    2. JELASKAN dengan rinci dan kritis.
    3. Pisahkan antara Penjelasan Utama (Main View) dan Detail Referensi (Dropdown).
    
    ATURAN PENTING:
    - LANGSUNG JAWAB SESUAI FORMAT DI BAWAH.
    - DILARANG menggunakan kata pembuka seperti "Baik", "Tentu", "Berikut analisis saya".
    - DILARANG mengulang input data di awal jawaban.
    
    DATA SAMPEL ML:
    - Input: {data_dict['kategori']} | {data_dict['bahan_baku']}
    - Kondisi: Suhu {data_dict['suhu']}°C | Waktu {data_dict['lama_simpan']} jam | pH {data_dict['ph']}
    - Fisik: Warna {data_dict['warna']} | Bau {data_dict['bau']} | Tekstur {data_dict['tekstur']}
    
    HASIL PREDIKSI SISTEM (ML):
    - Status: [{prediction_label}]
    - Risk Score: {risk_score:.1f}%

    --- FORMAT OUTPUT RESPONSE (WAJIB IKUTI) ---
    Pisahkan jawabanmu menjadi dua bagian dengan separator "|||REFERENSI|||".

    BAGIAN 1: PENJELASAN UTAMA (Tampil Langsung)
    (Jangan terlalu singkat! Berikan penjelasan "daging" yang berbobot seperti seorang konsultan ahli).
    
    ### 1. 🔍 Validasi & Analisis Risiko
    - Evaluasi apakah prediksi ML masuk akal.
    - Jelaskan interaksi Suhu vs Waktu vs Bakteri secara naratif yang mudah dipahami tapi tajam. 
    - Jika ML salah/bahaya, jelaskan letak kesalahannya dengan tegas.

    ### 2. 🛡️ Rekomendasi Penanganan
    - Langkah konkret (Cooking temp, storage method).
    - Solusi jika user ragu.

    ### 3. 🏁 KESIMPULAN AUDITOR (Final Verdict)
    - Status Akhir: [TETAP AMAN / TIDAK LAYAK / BERISIKO TINGGI]
    - Alasan Kunci (1 Paragraf).

    |||REFERENSI|||

    BAGIAN 2: LAMPIRAN AKADEMIS (Untuk Dropdown)
    (Bagian ini khusus untuk "nerd" moment, kalkulasi, dan daftar pustaka).
    
    ### 🔬 Landasan Teori & Kalkulasi Detail
    - **Teori Hurdle**: Jelaskan secara teknis interaksi faktor intrinsik/ekstrinsik.
    - **Kinetika Q10**: Tuliskan potensi laju pertumbuhan bakteri jika suhu naik 10°C (x2 atau x3).
    
    ### � Identifikasi Spesies & Toksikologi
    - Bakteri Target Spesifik (nama latin) dan karakteristiknya pada bahan ini.
    
    ### 📚 Daftar Pustaka Valid
    - Cantumkan referensi spesifik (SNI No. XXX, FDA BAM Chapter X, Jurnal YYY).
    """

    # Daftar model yang akan dicoba (Fallback mechanism)
    # Daftar model yang akan dicoba (Fallback mechanism)
    models_to_try = [
        'gemini-2.0-flash-lite',  # Lite version (Faster)
        'gemini-2.0-flash',       # Standard
        'gemini-flash-latest',    # Alias for latest stable
        'gemini-pro'              # Legacy
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
    st.subheader("🤖 Penjelasan Ahli AI (Auditor)")
    with st.spinner("Profesor sedang membedah jurnal & menghitung kinetika bakteri..."):
        full_explanation = generate_explanation(data_dict, pred_label, risk_score)
        
        # Split Response (Summary vs Scientific Deep Dive)
        if "|||REFERENSI|||" in full_explanation:
            parts = full_explanation.split("|||REFERENSI|||")
            summary_part = parts[0]
            science_part = parts[1]
            
            # Tampilkan Penjelasan Utama (Tetap Detail & Berbobot)
            st.markdown(summary_part)
            
            # Tampilkan Detail Referensi dalam Dropdown
            with st.expander("📚 Analisis Teoretis, Kalkulasi Q10 & Daftar Pustaka"):
                st.info("Bagian ini memuat detail akademis untuk keperluan riset/skripsi.")
                st.markdown(science_part)
        else:
            # Fallback jika format AI tidak sesuai
            st.markdown(full_explanation)

# --- ABOUT SECTION (ACADEMIC CONTEXT) ---
with st.expander("ℹ️ Tentang Aplikasi & Metode Ilmiah"):
    st.markdown("""
    ### Sistem Keputusan Kelayakan Pangan (Food Safety Decision System)
    
    **Tujuan:**
    Aplikasi ini dirancang untuk mendemokratisasi akses terhadap analisis keamanan pangan standar laboratorium. Menggunakan kecerdasan buatan untuk membantu mahasiswa Teknik Pangan, pelaku usaha, dan masyarakat umum dalam menilai kelayakan konsumsi makanan secara cepat dan akurat.

    **Metodologi:**
    1.  **Klasifikasi (Classification)**: Sistem menggunakan algoritma *Machine Learning* (Random Forest/Gradient Boosting) untuk mengklasifikasikan data input menjadi dua kelas: `AMAN` (1) atau `TIDAK AMAN` (0).
    2.  **Probabilitas Risiko**: Selain label biner, model menghitung *Risk Score* berdasarkan probabilitas prediksi (0-100%).
    3.  **Forensik AI**: Integrasi dengan LLM (Large Language Model) bertindak sebagai ahli mikrobiologi virtual untuk memberikan penjelasan kausalitas (sebab-akibat) berdasarkan parameter biokimia (pH, Suhu, Waktu).

    **Validasi:**
    Model dilatih menggunakan dataset pangan yang telah divalidasi dengan uji laboratorium standar, mencakup parameter fisik (organoleptik) dan lingkungan.
    """)
