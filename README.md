# PPD Risk Screening — Capstone Development Artifacts

Code that implements the design in Chapter Three ("System Analysis and Design") of the
capstone proposal "Machine Learning Model for Postpartum Depression Risk Classification
Among Postpartum Women in Senegal".

## Folder structure

```
ppd_project/
  data/
    post_natal_data.csv       # the real Kaggle "PostPartum Depression" dataset (Mosaraf, 2023)
  notebook/
    build_notebook.py         # generates ppd_model_training.ipynb
    ppd_model_training.ipynb  # data cleaning, feature engineering, model comparison (already executed)
    requirements.txt
  trained_model/
    model_bundle.joblib       # trained model + encoders, loaded by the API
    metrics.json               # comparison metrics for all 4 models
    model_comparison.png
    confusion_matrices.png
    feature_importance.png
  api/
    main.py                   # FastAPI app: auth, screening, clinical assessment, healthcare-worker endpoints
    models.py                 # SQLAlchemy ORM models (matches the ERD/class diagram)
    schemas.py                # Pydantic request/response schemas
    auth.py                   # JWT auth, password hashing, role-based access control
    ml_service.py             # loads model_bundle.joblib, runs predictions, crisis check
    database.py                # SQLAlchemy engine/session setup
    test_flow.py               # end-to-end smoke test (13 checks) — no server needed
    requirements.txt
  frontend/
    app.py                    # Streamlit app (mother + healthcare worker views, EN/FR)
    test_frontend.py          # end-to-end UI test against a running API
    requirements.txt
```

## The dataset

This project trains on the real Kaggle **"PostPartum Depression"** dataset (Mosaraf, 2023),
included at `data/post_natal_data.csv`. Two data-quality issues in the raw file are handled
explicitly by the notebook rather than hidden, and a third, more fundamental limitation of the
dataset was discovered while investigating the first two — all three should be discussed in
Chapter Four.

1. **Repeated answer patterns, with no reliable way to tell why.** The raw file has 1,503 rows
   but only 90 unique submission timestamps, and 78% of rows share their full set of answers
   with at least one other row. This *looks* like duplication, but there's no patient identifier
   in the data, so a repeated pattern could equally be two different mothers who genuinely gave
   the same answers on an 8-item scale with only 3 possible levels each — dropping those rows
   would silently throw away real respondents on an unverifiable assumption. The notebook
   (`build_notebook.py`, Section 4) keeps **all 1,491 valid rows** and instead makes the
   train/test split **group-aware**: `StratifiedGroupKFold` guarantees that no response pattern
   ("group") appears in both the training set and the test set, so whether or not a given
   repeat is a true duplicate, it can never leak between train and test. This is the
   leakage-safe fix for the question "are these duplicates," because it works regardless of the
   answer.
2. **Non-standard category labels.** A few columns use answer phrasing outside the clean
   No / Sometimes / Yes scale (e.g. "Two or more days a week", "Often", "Not at all", "Maybe",
   "Not interested to say"). The notebook normalises these onto the 3-level scale before
   encoding (see `VALUE_NORMALIZATION` in the loading cell). A declined self-harm answer
   ("Not interested to say") is mapped to "Sometimes", never to "No" — a non-answer must never
   be silently treated as safe.
3. **Label circularity (the more serious finding).** After fixing the split, a naive
   (non-group-aware) split and the group-aware split scored *identically* (0.993 accuracy,
   0.000 gap) — meaning duplicate-row leakage was not what was driving the high accuracy.
   Investigating further (notebook Section 4b) showed why: `risk_level`, the training label,
   is computed as a **deterministic tercile threshold on the sum of the same 8 symptom
   columns used as model input**. A trivial, untrained rule — "sum the 8 symptom scores, cut
   into thirds" — scores **1.000** on the held-out test set, beating every trained model.
   In other words, the dataset's label isn't an independent clinical judgment; it's a
   restatement of the input features under a different name, so *any* reasonable classifier
   will look excellent on this data regardless of whether it has learned anything clinically
   meaningful. This is the central limitation of the current dataset and is documented in the
   notebook itself, not just here — see the markdown/code cells immediately after Section 4b.
   The `ClinicalAssessment` feature (below) exists specifically to fix this for future data.

If you ever need to swap the dataset, just replace `data/post_natal_data.csv` — the notebook
falls back to a schema-matched synthetic dataset only if that file is missing, purely so it
still runs end to end in an empty environment.

## 1. Run the training notebook

```
cd notebook
pip install -r requirements.txt --break-system-packages
python3 build_notebook.py
jupyter nbconvert --to notebook --execute --inplace ppd_model_training.ipynb --ExecutePreprocessor.timeout=300
```

This produces `../trained_model/model_bundle.joblib`, which the API loads at request time.
The notebook has already been run once on the real data — the files in `trained_model/` are
from that run. **You don't need to rerun it** unless you change the training logic or the
dataset changes.

### Current results (real data, all 1,491 rows, group-aware 80/20 split)

| Model | Accuracy | F1 (macro) |
|---|---|---|
| **Logistic Regression (selected)** | 0.993 | 0.994 |
| XGBoost | 0.919 | — |
| Random Forest | 0.909 | — |
| SVM | 0.886 | — |

Logistic Regression was selected automatically (highest macro F1-score) and is what
`trained_model/model_bundle.joblib` contains. **Read these numbers alongside the label
circularity finding above** — a trivial threshold rule also scores 1.000 on the same test
set, so the near-perfect accuracy reflects how the label was defined, not how hard the
classification problem is. This distinction belongs in Chapter Four's discussion of results.

## 2. Run the API

```
cd api
pip install -r requirements.txt --break-system-packages
uvicorn main:app --reload
```

- Interactive docs: http://localhost:8000/docs
- The API defaults to a local SQLite file (`ppd.db`). To use PostgreSQL instead (as described
  in Chapter Three), set `DATABASE_URL`, e.g.:
  `export DATABASE_URL=postgresql://user:pass@host:5432/ppd_db`
- On first startup it seeds two demo facilities and a placeholder ML model record.

**If you hit `TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'`**
it means pip resolved an incompatible `fastapi`/`starlette` pair (this happens easily if
something else in the same virtual environment — like `streamlit` — pulls in a newer
`starlette` than `fastapi` expects). Fix it with:
```
pip install -r requirements.txt --force-reinstall
```
The versions pinned in `requirements.txt` are tested together and work in the same venv as
the frontend's `streamlit` dependency.

To verify everything works without starting a server:

```
cd api
python3 test_flow.py
```

This runs 13 checks end to end: facility listing, mother/worker registration, a low-risk
submission, a crisis-flagged submission, rejection of an incomplete form, history retrieval,
the healthcare worker's patient list, the facility-scoping 403 check, recording and reading
back an independent clinical assessment, a second 403 check for cross-facility assessment
attempts, and report generation (now including the clinical assessment).

## 3. Run the frontend

```
cd frontend
pip install -r requirements.txt --break-system-packages
streamlit run app.py
```

By default it talks to the API at `http://localhost:8000`. To point it elsewhere:

```
export API_BASE_URL=http://your-api-host:8000
streamlit run app.py
```

Open the URL Streamlit prints (works from a phone or computer browser — no install needed).
A language toggle (English / French) is available on the login page and in the sidebar once
logged in.

- **Mother flow:** register → log in → read and accept the consent notice → fill out the
  screening form → see the risk level and recommendation on the same page, with an immediate
  crisis message if self-harm thoughts are flagged → view past screenings under "My history",
  including any clinical assessment a healthcare worker has since recorded for that screening.
- **Healthcare worker flow:** register → log in → see the list of mothers registered at your
  own facility only → view a mother's screening history → record your own independent clinical
  assessment on a screening (separate from the ML prediction) → view facility-level risk
  analytics → generate a text report (includes the clinical assessment when one exists).

To verify the frontend against a running API without opening a browser:

```
cd frontend
python3 test_frontend.py
```

This drives the app with Streamlit's `AppTest` utility and checks: registration, login, the
consent gate (blocked without it, allowed with it), crisis-message display, history rendering,
the healthcare worker's patient list, recording and displaying a clinical assessment, the
facility analytics tab, report generation, and the French language toggle — all against the
live API.

## New since the initial delivery

Four additions were made in response to two concerns: that the training dataset's label is
circular (see above), and that the delivered app felt too basic to present as a capstone
demo or bring into a real facility.

1. **Independent clinical assessment.** A healthcare worker can record their own risk
   judgment for a screening (`POST /healthcare/screenings/{form_id}/assessment`,
   `api/models.py: ClinicalAssessment`), kept deliberately separate from the ML prediction on
   the same form. This isn't just a UI nicety — it's the practical fix for the label
   circularity problem above: a (form responses → clinician's independent judgment) pair,
   collected over time from real use, is a genuine, non-circular label a future retrain can
   use, unlike the current dataset's self-referential one.
2. **Consent notice.** The mother must check a consent statement — what her answers are used
   for, that a healthcare worker at her facility may see them, that her data stays private —
   before a screening form can be submitted (`frontend/app.py: show_mother_home`).
3. **French language toggle.** The full mother- and worker-facing interface (forms, labels,
   messages, risk levels) is available in English or French via a toggle on the login page and
   in the sidebar (`frontend/app.py: TRANSLATIONS`). The values sent to the API never change
   with the language — only the displayed labels do.
4. **Facility analytics.** A new tab on the healthcare worker's home page shows the
   distribution of latest risk levels and the count of crisis flags raised across every mother
   at the worker's own facility (`frontend/app.py: show_facility_analytics`), giving staff a
   facility-level view rather than only a per-patient one.

## Field names (frontend ↔ API ↔ model must all agree)

The screening form uses these exact field names everywhere — `frontend/app.py`
(`SYMPTOM_QUESTIONS`), `api/schemas.py` (`ScreeningFormIn`), and the notebook's
`SYMPTOM_COLS`/`RENAME_MAP` all use the same set:

`age_bracket`, `feeling_sad`, `irritable`, `trouble_sleeping`, `trouble_concentrating`,
`appetite_changes`, `feeling_anxious`, `feeling_guilty`, `bonding_difficulty`,
`self_harm_thoughts`.

`api/ml_service.py`'s `encode_form()` doesn't hardcode these names — it reads whatever
`feature_cols` the notebook saved into `model_bundle.joblib` and looks each one up in the
submitted form by that same name. If you ever rename a field, you only need to update it in
the notebook and in `frontend/app.py`/`schemas.py` — `ml_service.py` will follow automatically.

## Chapter Three → code map

| Chapter Three section | Code |
|---|---|
| 3.4 Data Definition and Acquisition | `notebook/build_notebook.py` (RENAME_MAP, VALUE_NORMALIZATION) |
| 3.4 ML training pipeline (cleaning, feature engineering, group-aware split, SMOTE, model comparison) | `notebook/ppd_model_training.ipynb` |
| 3.5.1 Frontend (Streamlit) | `frontend/app.py` |
| 3.5.2 Backend / API | `api/main.py` |
| Class diagram / ERD | `api/models.py` |
| Facility-scoped access control | `api/main.py` (`_get_mother_in_same_facility`), proven in `api/test_flow.py` steps 9 and 12 |
| Self-harm / crisis check (kept separate from the ML model) | `api/ml_service.py` (`check_self_harm`), `api/models.py` (`CrisisCheck`) |
| Home screening for mothers with risk-tiered recommendations | `api/ml_service.py` (`RECOMMENDATIONS`), `frontend/app.py` (`show_mother_home`) |
| Independent clinical assessment (non-circular future labels) | `api/models.py` (`ClinicalAssessment`), `api/main.py` (`add_clinical_assessment`), `frontend/app.py` (clinical assessment form in `show_worker_home`) |
| Informed consent before screening | `frontend/app.py` (`show_mother_home`, consent checkbox) |
| Facility analytics | `frontend/app.py` (`show_facility_analytics`) |

## Known limitations to state in Chapter Four

- **Label circularity** (see "The dataset" above) is the dataset's central limitation: the
  training label is a deterministic function of the same features used as model input, so
  reported accuracy/F1 reflect the label's construction more than genuine predictive
  difficulty. Report this alongside the metrics, not as a footnote.
- Risk-level thresholds are **data-driven terciles**, not clinically validated cutoffs (e.g.
  EPDS score bands) — this is also the root cause of the circularity above. Revisit if PRAMS,
  a validated clinical scale, or real facility-collected labels (via the new clinical
  assessment feature) become available.
- The dataset is US/international, self-administered via a Google Form, not Senegal-specific —
  the geographic mismatch flagged in supervisor feedback still applies and should be discussed
  as a limitation on generalisability to the target population.
- The **group-aware split** (`StratifiedGroupKFold` on the full response pattern) prevents
  identical answer patterns from crossing between train and test, but it cannot determine
  whether repeated patterns are true duplicates or different mothers who answered identically —
  that would require a patient identifier the dataset doesn't have.
- Authentication (JWT secret, password policy) is set up for development, not hardened for
  production deployment.
