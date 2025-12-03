# Sistem Keputusan Kelayakan Pangan (Food Safety Lab)

Aplikasi berbasis AI untuk menentukan kelayakan konsumsi makanan berdasarkan karakteristik fisik dan kondisi penyimpanan.

## Fitur Utama
- **Klasifikasi Keamanan**: Aman / Tidak Aman.
- **Risk Score**: Menghitung persentase risiko bahaya (0-100%).
- **AI Explanation**: Penjelasan ilmiah menggunakan OpenAI GPT (Biokimia, Mikrobiologi, Rekomendasi).
- **Offline Mode**: Fallback penjelasan rule-based jika tidak ada koneksi internet/API Key.
- **Parameter Lengkap**: Suhu, Lama Simpan, pH, Warna, Bau, Tekstur.

## Cara Menjalankan
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Jalankan aplikasi:
    ```bash
    streamlit run app.py
    ```

## Teknologi
- Python
- Streamlit
- Scikit-Learn (Random Forest)
- OpenAI API
- Pandas & NumPy

## Struktur Project
- `app.py`: Main application code.
- `training.py`: Script untuk melatih model Machine Learning.
- `dataset_pangan.csv`: Dataset yang digunakan.
- `model.pkl`: Model Random Forest yang sudah dilatih.
