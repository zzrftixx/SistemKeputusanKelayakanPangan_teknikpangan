import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import joblib
import os
import shutil

# Path Configuration
BASE_CSV = "../csv/dataset_pangan.csv"
NEW_DATA_CSV = "labeled_samples.csv"
MODEL_PATH = "../model.pkl"

def retrain_model():
    print("🔄 Memulai proses Retraining...")
    
    # 1. Load Original Data
    if os.path.exists(BASE_CSV):
        df_base = pd.read_csv(BASE_CSV)
    else:
        print("❌ Dataset dasar tidak ditemukan!")
        return None

    # 2. Load New Evidence (AI Labeled)
    if os.path.exists(NEW_DATA_CSV):
        df_new = pd.read_csv(NEW_DATA_CSV)
        print(f"📥 Menemukan {len(df_new)} data baru dari AI.")
    else:
        print("⚠️ Tidak ada data baru untuk dilatih.")
        return None
    
    # 3. Merge Data (Augmentation)
    # Pastikan kolom sama
    try:
        df_combined = pd.concat([df_base, df_new], ignore_index=True)
        # Drop duplicates untuk menjaga kesehatan data
        df_combined.drop_duplicates(inplace=True)
    except Exception as e:
        print(f"❌ Gagal merge data: {e}")
        return None

    # 4. Training Process (Standard Sklearn)
    X = df_combined.drop("aman_dimakan", axis=1)
    y = df_combined["aman_dimakan"]

    categorical_features = ["kategori", "bahan_baku", "warna", "bau", "tekstur"]
    numerical_features = ["suhu", "lama_simpan", "ph"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )

    pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(n_estimators=100, random_state=42))
    ])

    # Train
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    pipeline.fit(X_train, y_train)
    
    # Evaluation
    acc = pipeline.score(X_test, y_test)
    print(f"📈 Akurasi Model Baru: {acc:.2%}")

    # 5. Commit Changes
    # Simpan Dataset Baru (Overwrite base untuk evolusi)
    # Backup dulu
    shutil.copy(BASE_CSV, BASE_CSV + ".bak")
    df_combined.to_csv(BASE_CSV, index=False)
    print("💾 Dataset utama telah diperbarui (+Data AI).")

    # Simpan Model Baru
    joblib.dump(pipeline, MODEL_PATH)
    print("🚀 Model berhasil di-update dan siap dipakai.")

    return acc

if __name__ == "__main__":
    retrain_model()
