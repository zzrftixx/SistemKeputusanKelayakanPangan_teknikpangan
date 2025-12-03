import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
import joblib
import os

# Load dataset
# Cek path, jika tidak ada di csv/ coba cari di root atau parent
if os.path.exists("csv/dataset_pangan.csv"):
    df = pd.read_csv("csv/dataset_pangan.csv")
elif os.path.exists("../csv/dataset_pangan.csv"):
    df = pd.read_csv("../csv/dataset_pangan.csv")
else:
    df = pd.read_csv("dataset_pangan.csv")

# Pisahkan fitur dan target
X = df.drop("aman_dimakan", axis=1)
y = df["aman_dimakan"]

# Definisi kolom
categorical_features = ["kategori", "bahan_baku", "warna", "bau", "tekstur"]
numerical_features = ["suhu", "lama_simpan", "ph"]

# Preprocessing
preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), numerical_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ]
)

# Pipeline
model = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(n_estimators=100, random_state=42))
])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model.fit(X_train, y_train)

# Simpan model (pipeline sudah termasuk preprocessor)
# Simpan di folder model/ atau root jika tidak ada
output_path = "model.pkl"
if os.path.exists("../model.pkl"): # Jika dijalankan dari folder training/
    output_path = "../model.pkl"

joblib.dump(model, output_path)

print(f"MODEL PIPELINE SUDAH DISIMPAN DI {output_path}")
