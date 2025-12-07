import google.generativeai as genai
import pandas as pd
import os
import json
import time

# Konfigurasi API Key (Dynamic)
def configure_api(api_key=None):
    if not api_key:
        # Coba cari di env atau secrets files
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            try:
                with open("../.streamlit/secrets.toml", "r") as f:
                    for line in f:
                        if "GEMINI_API_KEY" in line:
                            api_key = line.split("=")[1].strip().strip('"')
                            break
            except:
                pass
    
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def generate_edge_cases(n=10, api_key=None):
    """
    Meminta AI untuk membuat N data sampel 'Jebakan' (Edge Cases)
    yang mungkin salah diprediksi oleh model biasa.
    """
    if api_key:
        genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    Bertindaklah sebagai "Adversarial AI Tester". Tugasmu adalah membuat {n} data sampel keamanan pangan yang "Tricky" atau "Menjebak".
    Fokus pada kasus:
    1. Secara fisik terlihat bagus (Warna/Bau Normal) TAPI tidak aman karena Suhu/Waktu (False Negative).
    2. Secara fisik terlihat busuk TAPI mungkin aman (jarang, tapi bisa untuk fermentasi).
    3. Kasus batas (Beda pH sedikit, beda suhu sedikit).
    
    Output WAJIB format JSON list of objects dengan key:
    - kategori (pilih: Daging, Sayur, Buah, Susu, Ikan, Lainnya)
    - bahan_baku (nama spesifik)
    - warna (pilih: merah segar, pucat, kecoklatan, dll)
    - bau (pilih: normal, busuk, asam, amis, dll)
    - tekstur (pilih: kenyal, lembek, berlendir, dll)
    - suhu (integer, celcius)
    - lama_simpan (integer, jam)
    - ph (float, eksak)
    
    CONTOH OUTPUT RAW JSON SAJA:
    [
        {{"kategori": "Daging", "bahan_baku": "Daging Sapi", "warna": "merah segar", "bau": "normal", "tekstur": "kenyal", "suhu": 30, "lama_simpan": 6, "ph": 6.0}},
        ...
    ]
    """
    
    max_retries = 3
    base_delay = 10
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            # Bersihkan markdown formatting ```json ... ```
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            if "429" in str(e) or "Quota exceeded" in str(e):
                wait_time = base_delay * (attempt + 1)
                print(f"⚠️ Quota Exceeded. Menunggu {wait_time} detik sebelum retry...")
                time.sleep(wait_time)
            else:
                print(f"⚠️ Gagal generate data: {e}")
                return pd.DataFrame()
    
    print("❌ Gagal generate setelah beberapa percobaan.")
    return pd.DataFrame()

if __name__ == "__main__":
    print("🤖 Sedang membuat soal ujian susah buat AI...")
    df_new = generate_edge_cases(10)
    if not df_new.empty:
        print("✅ Berhasil generate data:")
        print(df_new.head())
        # Simpan sementara
        df_new.to_csv("generated_samples.csv", index=False)
    else:
        print("❌ Gagal.")
