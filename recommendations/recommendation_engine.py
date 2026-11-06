import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "NLP_dataset_500.xlsx"

def build_recommendations(prediction, profile=None, query_text=""):
    df = pd.read_excel(DATA)
    profile = profile or {}
    goal = str(profile.get("health_goal") or "").strip().lower()
    diet = str(profile.get("diet_preference") or "").strip().lower()
    allergies = [x.strip().lower() for x in str(profile.get("allergies") or "").split(",") if x.strip()]
    intent = prediction["intent"]
    subset = df[df["Intent"].astype(str).str.lower() == intent.lower()].copy()
    if goal and "Health goal" in subset:
        matched = subset[subset["Health goal"].astype(str).str.lower().str.contains(goal, na=False)]
        if not matched.empty: subset = matched
    if diet and "Diet Type" in subset:
        matched = subset[subset["Diet Type"].astype(str).str.lower() == diet]
        if not matched.empty: subset = matched
    # Filter obvious allergy terms from food and nutrient labels.
    if allergies:
        mask = ~subset["Food Item"].astype(str).str.lower().apply(lambda s: any(a in s for a in allergies))
        subset = subset[mask]
    if subset.empty:
        subset = df[df["Intent"].astype(str).str.lower() == intent.lower()]
    items = []
    for _, row in subset.drop_duplicates(subset=["Food Item"]).head(6).iterrows():
        items.append({
            "food": str(row.get("Food Item", "Food item")),
            "nutrients": str(row.get("Nutrient", "Not listed")),
            "meal": str(row.get("Meal", "Flexible")),
            "dataset_goal": str(row.get("Health goal", "Not specified")),
            "diet_type": str(row.get("Diet Type", "Not specified"))
        })
    return {
        "title": f"Dataset-based ideas for: {intent}",
        "items": items,
        "guidance": "These suggestions summarize associations present in your uploaded dataset. Nutrient labels are reproduced as supplied; no per-serving quantities or clinical benefits are inferred.",
        "safety": "General educational information only. This is not a diagnosis or medical diet plan. If you have diabetes, allergies, kidney disease, are pregnant, or take medication, consult a registered dietitian or clinician before changing your diet."
    }
