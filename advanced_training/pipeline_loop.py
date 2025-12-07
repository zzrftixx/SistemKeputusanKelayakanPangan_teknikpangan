import time
import pandas as pd
import generator
import labeler
import trainer
import sys
import getpass
import os

def main_loop(max_iterations=50):
    print("🚀 MEMULAI SISTEM ACTIVE LEARNING LOOP (AI-DRIVEN)")
    
    # 0. Setup API Key (Auto-Detect)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            # Cari di secrets.toml
            with open("../.streamlit/secrets.toml", "r") as f:
                for line in f:
                    if "GEMINI_API_KEY" in line:
                        api_key = line.split("=")[1].strip().strip('"')
                        break
        except:
            pass
            
    if not api_key:
        print("\n🔑 Masukkan Google Gemini API Key Anda:")
        api_key = getpass.getpass(prompt="API Key: ") # Aman, hidden input
        if not api_key:
             api_key = input("API Key (Visible): ") # Fallback

    if not api_key:
        print("❌ API Key wajib diisi untuk menjalankan AI Loop.")
        return

    print("✅ API Key terdeteksi. Memulai Loop...")
    print("Tekan CTRL+C untuk menghentikan loop.")
    
    iteration = 1
    total_acc = 0
    
    try:
        while True:
            if iteration > max_iterations:
                print("🏁 Batas iterasi tercapai.")
                break
                
            print(f"\n{'='*40}")
            print(f"🔄 ITERASI KE-{iteration}")
            print(f"{'='*40}")
            
            # 1. Generate Samples
            print("1. 🧠 Minta Gemini buat soal susah...")
            df_gen = generator.generate_edge_cases(n=10, api_key=api_key)
            if df_gen.empty:
                print("⚠️ Gagal generate, coba lagi nanti...")
                time.sleep(5)
                continue
            df_gen.to_csv("generated_samples.csv", index=False)
            
            # 2. Label Samples
            print("2. ⚖️ Minta AI Auditor mengoreksi jawaban...")
            df_labeled = labeler.label_data("generated_samples.csv", api_key=api_key)
            if df_labeled.empty:
                print("⚠️ Gagal labeling.")
                continue
            df_labeled.to_csv("labeled_samples.csv", index=False)
            
            # 3. Retrain Model
            print("3. 🏋️ Melatih ulang model dengan data baru...")
            accuracy = trainer.retrain_model()
            
            if accuracy:
                total_acc = accuracy
                print(f"✅ Iterasi {iteration} Selesai. Akurasi saat ini: {accuracy:.2%}")
            
            iteration += 1
            print("⏳ Istirahat 60 detik (Cooling Down)...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n🛑 Loop dihentikan oleh User.")
        print("Sistem telah menyimpan model terakhir yang paling pintar.")
        sys.exit()

if __name__ == "__main__":
    main_loop(100) # Bisa jalan sampai 100x putaran otomatis
