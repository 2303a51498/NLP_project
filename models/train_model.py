import os, json, sys, warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, ConfusionMatrixDisplay
from preprocessing.text_preprocessing import normalize_text

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "NLP_dataset_500.xlsx"
MODEL_DIR = BASE / "models"
REPORT_DIR = BASE / "reports"
MODEL_DIR.mkdir(exist_ok=True); REPORT_DIR.mkdir(exist_ok=True)

def main():
    if not DATA.exists():
        raise FileNotFoundError(f"Dataset missing: {DATA}")
    df = pd.read_excel(DATA)
    required = ["Original Query", "Intent"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset must contain columns: {missing}")
    df = df.dropna(subset=required).copy()
    df["clean_query"] = df["Original Query"].map(normalize_text)
    df["Intent"] = df["Intent"].astype(str).str.strip()
    df = df[(df.clean_query != "") & (df.Intent != "")]
    # Deduplicate exact query-label pairs before splitting.
    df = df.drop_duplicates(subset=["clean_query", "Intent"])
    counts = df["Intent"].value_counts()
    eligible = counts[counts >= 2].index
    df = df[df.Intent.isin(eligible)]
    X, y = df.clean_query, df.Intent
    if y.nunique() < 2:
        raise ValueError("At least two intent classes with two examples each are required.")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1,2), analyzer="char_wb",
                                  min_df=1, max_features=25000, sublinear_tf=True)),
        ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced",
                                          solver="lbfgs"))
    ])
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)
    report = classification_report(y_test, pred, zero_division=0)
    joblib.dump(model, MODEL_DIR / "nutrition_classifier.joblib")
    # Compatibility artifacts are also saved separately for transparent inspection.
    joblib.dump(model.named_steps["tfidf"], MODEL_DIR / "vectorizer.pkl")
    joblib.dump(model.named_steps["classifier"], MODEL_DIR / "classifier.pkl")
    labels = sorted(y.unique())
    cm = confusion_matrix(y_test, pred, labels=labels)
    fig, ax = plt.subplots(figsize=(max(8, len(labels)*0.8), max(6, len(labels)*0.65)))
    ConfusionMatrixDisplay(cm, display_labels=labels).plot(
        ax=ax, xticks_rotation=45, colorbar=False, cmap="Greens"
    )
    fig.tight_layout(); fig.savefig(REPORT_DIR / "confusion_matrix.png", dpi=160); plt.close(fig)
    summary = {
        "dataset_file": "data/NLP_dataset_500.xlsx",
        "original_shape": list(pd.read_excel(DATA).shape),
        "training_rows_after_cleaning": int(len(df)),
        "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "intent_distribution": {str(k): int(v) for k,v in counts.items()},
        "language_distribution": {str(k): int(v) for k,v in pd.read_excel(DATA)["Language "].fillna("Unknown").value_counts().items()} if "Language " in pd.read_excel(DATA).columns else {},
        "accuracy": float(acc),
        "evaluation_note": "Held-out stratified 20% split; results are dataset-specific and not evidence of clinical validity.",
        "classification_report": report
    }
    (REPORT_DIR / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with open(REPORT_DIR / "evaluation.txt", "w", encoding="utf-8") as f:
        f.write("NUTRITION QUERY INTENT CLASSIFIER — EVALUATION\n")
        f.write("="*55 + "\n")
        f.write(f"Dataset shape: {summary['original_shape']}\n")
        f.write(f"Rows used: {len(df)} | Train: {len(X_train)} | Test: {len(X_test)}\n")
        f.write(f"Accuracy: {acc:.4f}\n\n")
        f.write(report)
        f.write("\n\nLanguage limitation: all rows in this source dataset are labeled Telugu-English. ")
        f.write("The model is therefore not validated for standalone Hindi, Tamil, or English queries.\n")
        f.write("Confidence is a model probability, not medical certainty.\n")
    print(f"Trained on {len(X_train)} rows; tested on {len(X_test)} rows; accuracy={acc:.4f}")
    print(report)

if __name__ == "__main__":
    main()
