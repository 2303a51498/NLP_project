import os, joblib, numpy as np
from config import MODEL_DIR
from preprocessing.text_preprocessing import normalize_text

_model = None
def load_model():
    global _model
    if _model is None:
        path = os.path.join(MODEL_DIR, "nutrition_classifier.joblib")
        if not os.path.exists(path):
            raise RuntimeError("Trained model not found. Run: python models/train_model.py")
        _model = joblib.load(path)
    return _model

def predict_query(query):
    model = load_model()
    clean = normalize_text(query)
    if not clean:
        raise ValueError("Please enter a nutrition question.")
    probabilities = model.predict_proba([clean])[0]
    classes = model.named_steps["classifier"].classes_
    order = np.argsort(probabilities)[::-1]
    top = [{"intent": str(classes[i]), "confidence": float(probabilities[i])} for i in order[:3]]
    return {"intent": top[0]["intent"], "confidence": top[0]["confidence"], "top_predictions": top}
