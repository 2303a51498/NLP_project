# NutriQuery — Multilingual NLP-Based Personalized Nutrition Query Classification

Academic Flask + SQLite + scikit-learn project built using the supplied `NLP_dataset_500.xlsx`.

## Dataset inspection

The supplied workbook has **500 rows and 10 columns**:
`ID`, `Original Query`, `Language `, `Intent`, `Food Item`, `Nutrient`, `Meal`,
`Health goal`, `Diet Type`, `Area`.

The workbook contains no missing values in the inspected rows and 500 unique query strings.
All 500 examples are labeled **Telugu- English** in the language column. There are 11 intent labels:
Food nutrition (127), Weight Loss (77), General Nutrition (68), Healthy diet (65),
Diabetes management (41), Protein (36), Fitness Nutrition (26), Weight management (20),
child nutrition (20), Meal Planning (12), Weight gain (8).
The source dataset is the primary training and recommendation source; it is copied unchanged into `data/`.

**Language limitation:** the dataset does not provide labeled standalone Hindi, Tamil, or English examples.
The app preserves Unicode and detects Telugu/Devanagari/Tamil/Latin scripts heuristically, but classification quality is only trained/evaluated on the Telugu-English query style represented by this workbook. Add manually reviewed, labeled examples for other languages before claiming support.

## Features

- Registration/login with Werkzeug password hashing.
- Optional profile and preference fields.
- Query intent classification using character n-gram TF-IDF + Logistic Regression.
- Top-3 class probabilities and heuristic script detection.
- Dataset-derived food/meal suggestions filtered by intent, goal and diet preference.
- SQLite user, profile, query, classification and recommendation-history tables.
- Dashboard, searchable query history and clear-history action.
- Session-protected JSON endpoint: `POST /api/classify`.
- Evaluation report, metrics JSON and confusion-matrix image.

## Windows / VS Code setup

Use Python 3.10 or 3.11.

```powershell
cd nutrition_nlp_system
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

## Train the model

```powershell
python models/train_model.py
```

Training uses the workbook in `data/NLP_dataset_500.xlsx`, drops unusable rows and exact query-label duplicates, then performs a stratified 80/20 split with a fixed random seed. TF-IDF is fitted only on the training partition through the scikit-learn pipeline, avoiding vocabulary leakage. The script saves:
- `models/nutrition_classifier.joblib`
- `models/vectorizer.pkl`
- `models/classifier.pkl`
- `reports/evaluation.txt`
- `reports/metrics.json`
- `reports/confusion_matrix.png`

Do not report an accuracy number from another machine/run; use the generated `reports/metrics.json` and evaluation report.

## Run Flask

```powershell
python app.py
```

Open http://127.0.0.1:5000 and register an account. SQLite schema is initialized automatically at `instance/nutrition.db`.

## Sample questions

- `ragi daily thinte weight thagguthunda`
- `sugar unna vallu ragi roju teeskocha`
- `ragi breakfast lo thinte energy full day untunda`
- `weight loss kosam rice badalu ragi thinacha`

## API

Login in the browser first (the endpoint uses the same Flask session cookie), then send JSON:

```powershell
$body = @{ query = "ragi daily thinte weight thagguthunda" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:5000/api/classify -Method Post -ContentType "application/json" -Body $body -WebSession $session
```

For a quick curl request after obtaining a logged-in session cookie:
```bash
curl -X POST http://127.0.0.1:5000/api/classify \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{"query":"ragi daily thinte weight thagguthunda"}'
```

## Database tables

- `users`: identity, unique email, password hash, registration timestamp.
- `user_profiles`: age, gender, weight, height, dietary preference, goal, activity and allergies.
- `nutrition_queries`: original query, heuristic language label and timestamp.
- `classification_results`: predicted intent, model confidence, representative food and top predictions.
- `recommendation_history`: JSON snapshot of recommendations associated with each saved query.

All SQL values are passed as parameters. Foreign keys cascade when a user or query is deleted.

## Architecture / ML workflow

Browser (HTML/CSS/JS) → Flask routes/session → text normalization and script heuristic →
saved scikit-learn pipeline (character n-gram TF-IDF → Logistic Regression) → dataset-driven
recommendation filtering → SQLite persistence → result/dashboard templates.

Character n-grams are used because the source includes Romanized Telugu spelling variation.
The language detector only identifies script families; it cannot reliably distinguish English
from Romanized Telugu written in Latin characters.

## Nutrition safety and interpretation

Recommendations list the exact food, nutrient-label, meal and goal fields associated with
rows in the supplied workbook. They do **not** infer nutrient quantities, calorie values,
portion sizes or clinical effects. Dataset associations are not medical evidence. The app is
an academic demonstration, not a diagnosis or treatment tool. Users with diabetes, food
allergies, kidney disease, pregnancy or medication-related dietary needs should consult a
registered dietitian or clinician. Allergy filtering is a simple text match and is not a
guarantee against cross-contamination or hidden ingredients.

## Notes

- The first registered user is not automatically an admin; no admin role was requested.
- The Flask development server is for local academic demonstration only. For deployment,
  set a strong `SECRET_KEY`, disable debug mode and use a production WSGI server.
- The dashboard's registered-user count is global; query totals and history are per account.
