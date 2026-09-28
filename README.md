# PPD Risk Screening — Development Deliverables

This folder contains the development work for Chapter Four of the capstone: the model
training notebook and the FastAPI backend described in Chapter Three.

## What's here

```
ppd_project/
├── notebook/
│   └── ppd_model_training.ipynb   <- run this first
├── data/
│   └── (put your real dataset CSV here — see below)
├── trained_model/                 <- created by the notebook
│   ├── model_bundle.joblib
│   ├── metrics.json
│   ├── model_comparison.png
│   ├── confusion_matrices.png
│   └── feature_importance.png
└── api/
    ├── main.py            <- FastAPI app, run this second
    ├── database.py
    ├── models.py           <- SQLAlchemy ORM (matches your ERD)
    ├── schemas.py          <- Pydantic request/response models
    ├── auth.py             <- registration/login, JWT
    ├── ml_service.py       <- loads the trained model, predicts, crisis check
    ├── requirements.txt
    └── test_flow.py        <- end-to-end smoke test, no server needed
```

## 1. Run the notebook first

The notebook currently trains on **synthetic demo data** that mirrors the real Kaggle
"PostPartum Depression" dataset's schema, because the real file wasn't available in this
environment and PRAMS access was still pending. To use your real data:

1. Download the dataset (from Kaggle, or your approved PRAMS extract, mapped to the same
   column names — the notebook's second cell shows the exact mapping).
2. Save it as `data/post_natal_data.csv`.
3. Re-run the notebook top to bottom. No code changes needed — it automatically detects
   and uses the real file instead of generating synthetic data.

Running the notebook produces `trained_model/model_bundle.joblib`, which the API loads
automatically.

```bash
cd notebook
pip install -r ../api/requirements.txt jupyter imbalanced-learn matplotlib
jupyter nbconvert --to notebook --execute --inplace ppd_model_training.ipynb
```

## 2. Run the API

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive Swagger UI, where you can try
every endpoint directly in the browser.

By default the API uses a local SQLite file (`ppd.db`) so it runs with zero setup. To use
PostgreSQL as specified in Chapter Three, set an environment variable before starting it:

```bash
export DATABASE_URL="postgresql://user:password@host:5432/ppd_db"
uvicorn main:app --reload
```

## 3. Verify everything works

```bash
cd api
python3 test_flow.py
```

This runs an end-to-end test with no server needed: registers a mother and two healthcare
workers at two different facilities, submits screening forms (including one that trips the
crisis flag), confirms an incomplete form is rejected, and confirms a healthcare worker at
one facility cannot see a mother registered at a different facility.

## How this maps back to Chapter Three

| Chapter Three item | Where it is in this code |
|---|---|
| Functional requirements 1–11 | `api/main.py` endpoints |
| ERD (facilities, users, screening_forms, predictions, crisis_checks, models, reports) | `api/models.py` |
| Class diagram | `api/models.py` (structure) + `api/schemas.py` (behavior/validation) |
| "Self-harm question checked separately from the ML model" | `ml_service.check_self_harm()` vs `ml_service.predict_risk()` — two independent functions |
| Facility-scoped access for healthcare workers | `main._get_mother_in_same_facility()` |
| Model comparison (XGBoost, RF, SVM, LR) | `notebook/ppd_model_training.ipynb`, section 7 |
| Data-quality screening (duplicate rows) | `notebook/ppd_model_training.ipynb`, section 3 |
| Low/medium/high risk + recommendation text | `ml_service.RECOMMENDATIONS` |

## Known limitations to state in Chapter Four

- The model is currently trained on **synthetic data**, not the real dataset. Results in
  `trained_model/metrics.json` are not real performance figures until you swap in real
  data.
- The `risk_level` thresholds are tercile-based (see notebook section 4) because the
  Kaggle dataset doesn't include a validated EPDS score. If PRAMS data with an EPDS item
  becomes available, switch to the standard clinical cutoff instead.
- Authentication here is JWT-based and functional, but has not been hardened for
  production (e.g., no rate limiting, no email verification, no password reset flow) —
  fine for a capstone demo, worth flagging as future work if asked.
