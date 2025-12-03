import streamlit as st
import pandas as pd
import joblib
import numpy as np
import openai

st.set_page_config(page_title="Food Safety Lab", layout="wide")

# Sidebar untuk Konfigurasi AI
with st.sidebar:
    st.header("⚙️ Konfigurasi AI")
    # API Key dari user (Pre-filled)
    # NOTE: Jangan hardcode API Key di sini jika ingin deploy ke public repo!
    # Gunakan Streamlit Secrets atau Environment Variables.
    default_key = "" 
    api_key = st.text_input("OpenAI API Key", value=default_key, type="password", help="Masukkan API Key untuk fitur penjelasan AI.")
    
    if api_key:
        openai.api_key = api_key
        st.success("API Key terdeteksi!")
    else:
        st.warning("Masukkan API Key untuk mengaktifkan fitur penjelasan.")

st.title("Sistem Keputusan Kelayakan Pangan (Klasifikasi Makanan Aman / Tidak Aman)")

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

# Fungsi Penjelasan Offline (Rule-Based)
def generate_offline_explanation(data_dict, prediction_label, risk_score):
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

    return f"""
    ### ⚠️ Mode Offline (AI Tidak Terhubung)
    
    **Analisis Sistem:**
    *   **Status**: {prediction_label}
    *   **Deteksi Anomali**: {reason_text}
    *   **Saran**: {rec_text}
    
    *Catatan: Masukkan API Key OpenAI yang valid untuk penjelasan ilmiah super detail.*
    """

# Fungsi Penjelasan AI
def generate_explanation(data_dict, prediction_label, risk_score):
    if not api_key:
        return generate_offline_explanation(data_dict, prediction_label, risk_score)
    
    prompt = f"""
    Kamu adalah Profesor Ahli Mikrobiologi dan Keamanan Pangan (Food Safety Scientist).
    Lakukan analisis forensik mendalam terhadap sampel makanan berikut:

    DATA SAMPEL:
    - Kategori: {data_dict['kategori']}
    - Bahan: {data_dict['bahan_baku']}
    - Ciri Fisik: Warna {data_dict['warna']}, Bau {data_dict['bau']}, Tekstur {data_dict['tekstur']}
    - Parameter Lingkungan: Suhu {data_dict['suhu']}°C, Waktu {data_dict['lama_simpan']} jam, pH {data_dict['ph']}

    HASIL LAB:
    - Prediksi: {prediction_label}
    - Tingkat Risiko: {risk_score:.1f}%

    TUGAS ANALISIS (Jawab dengan format Markdown yang rapi):
    1. **Diagnosa Ilmiah**: Jelaskan mekanisme biokimia yang terjadi. Mengapa kombinasi suhu {data_dict['suhu']}°C dan pH {data_dict['ph']} menyebabkan kondisi ini? Jelaskan proses denaturasi atau fermentasi yang relevan.
    2. **Analisis Mikrobiologi**: Identifikasi 2-3 patogen spesifik yang paling mungkin tumbuh di media {data_dict['kategori']} dengan kondisi ini (misal: Salmonella sp., Listeria, Clostridium botulinum, Bacillus cereus, atau jamur Rhizopus). Jelaskan bahayanya.
    3. **Rekomendasi Penanganan Kritis**: Berikan instruksi langkah demi langkah. Jika aman, bagaimana cara menyimpannya agar tetap awet? Jika bahaya, bagaimana cara membuangnya agar tidak mengkontaminasi lingkungan?
    
    Gunakan bahasa yang otoritatif, ilmiah, namun mudah dipahami. Berikan fakta mengejutkan jika ada.
    """

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Kamu adalah Profesor Keamanan Pangan kelas dunia."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        # Fallback ke offline jika error (misal kuota habis)
        return generate_offline_explanation(data_dict, prediction_label, risk_score)

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

    st.divider()
    st.subheader("Hasil Analisis Laboratorium")

    col_res1, col_res2 = st.columns(2)

    pred_label = "AMAN DIMAKAN" if prediction == 1 else "TIDAK AMAN / BERBAHAYA"

    with col_res1:
        if prediction == 1:
            st.success(f"✅ STATUS: {pred_label}")
        else:
            st.error(f"⚠️ STATUS: {pred_label}")

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
        # Prepare data dict for prompt
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
        explanation = generate_explanation(data_dict, pred_label, risk_score)
        st.markdown(explanation)
