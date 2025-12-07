import google.generativeai as genai
import pandas as pd
import os
import time

# Konfigurasi API (Dynamic)
def configure_api(api_key=None):
    if api_key:
        genai.configure(api_key=api_key)
        return

    # Fallback checks
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        try:
            with open("../.streamlit/secrets.toml", "r") as f:
                for line in f:
                    if "GEMINI_API_KEY" in line:
                        key = line.split("=")[1].strip().strip('"')
                        break
        except:
            pass
    if key:
        genai.configure(api_key=key)

def label_data(input_file="generated_samples.csv", api_key=None):
    if api_key:
        genai.configure(api_key=api_key)

    if not os.path.exists(input_file):
        print("⚠️ File input tidak ada.")
        return pd.DataFrame()

    df = pd.read_csv(input_file)
    print(f"🔍 Melabeli {len(df)} data...")
    
    labels = []
    reasons = []

    model = genai.GenerativeModel('gemini-2.0-flash')
    
    for index, row in df.iterrows():
        # Prompt Strict Auditor
        prompt = f"""
        Bertindaklah sebagai "Profesor Keamanan Pangan" yang SANGAT KETAT.
        Tentukan apakah sampel makanan ini AMAN (1) atau BERBAHAYA (0).
        
        Kondisi:
        - Bahan: {row['bahan_baku']} ({row['kategori']})
        - Fisik: Warna {row['warna']}, Bau {row['bau']}, Tekstur {row['tekstur']}
        - Lingkungan: Suhu {row['suhu']} C, Lama {row['lama_simpan']} jam
        - pH: {row['ph']}
        
        Aturan Fatal:
        - Suhu > 5C dan < 60C selama > 2-4 jam untuk daging/susu = BAHAYA (0).
        - Bau busuk/asem = BAHAYA (0).
        - pH tidak sesuai spek bahan = BAHAYA (0).
        
        Jawab hanya dengan angka: 1 (Aman) atau 0 (Bahaya).
        """
        
        max_retries = 3
        base_delay = 5
        
        success = False
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                verdict = response.text.strip()
                
                # Parsing jawaban kasar (kadang AI cerewet)
                if "0" in verdict:
                    lbl = 0
                elif "1" in verdict:
                    lbl = 1
                else:
                    lbl = 0 # Default Paranoid
                
                labels.append(lbl)
                print(f"[{index+1}] {row['bahan_baku']} ({row['suhu']}C/{row['lama_simpan']}h) -> Label: {lbl}")
                time.sleep(2) # Normal rate limit buffer
                success = True
                break # Berhasil, keluar dari loop retry
                
            except Exception as e:
                if "429" in str(e) or "Quota exceeded" in str(e):
                    wait_time = base_delay * (attempt + 1)
                    print(f"⏳ Kena Limit (429). Tunggu {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Error labeling: {e}")
                    break
        
        if not success:
            labels.append(0) # Fail safe jika retry habis

    df['aman_dimakan'] = labels
    return df

if __name__ == "__main__":
    df_labeled = label_data()
    if not df_labeled.empty:
        df_labeled.to_csv("labeled_samples.csv", index=False)
        print("✅ Data berhasil dilabeli dan disimpan ke labeled_samples.csv")
