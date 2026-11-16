"""
Export screening data as a de-identified CSV for retraining.

Run from the api/ folder:
    python3 export_training_data.py                  # only rows with a clinician label
    python3 export_training_data.py --include-unlabeled
    python3 export_training_data.py --out my_export.csv

Each row = one screening: the 9 form answers + age bracket, the clinician's independent
risk level (`clinical_label`, the non-circular training label), the ML prediction made at
the time (`ml_prediction`, for comparing model vs. clinician), and facility/submission month.

Privacy: no name, email, or user id is exported. `patient_key` is a salted hash of the mother's
id so repeat screenings of the same mother can be grouped (needed for a leakage-safe
group-aware split, as in the notebook) without revealing who she is. Set EXPORT_SALT in the
environment to a secret value so keys can't be reversed by guessing ids.

If a screening has several clinical assessments, the most recent one is used.
"""
import argparse
import csv
import hashlib
import json
import os

from database import SessionLocal
import models as m

FORM_FIELDS = [
    "age_bracket", "feeling_sad", "irritable", "trouble_sleeping", "trouble_concentrating",
    "appetite_changes", "feeling_anxious", "feeling_guilty", "bonding_difficulty",
    "self_harm_thoughts",
]


def patient_key(mother_id: str) -> str:
    salt = os.environ.get("EXPORT_SALT", "change-me")
    return hashlib.sha256(f"{salt}:{mother_id}".encode()).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="training_export.csv")
    parser.add_argument("--include-unlabeled", action="store_true",
                        help="also export screenings no clinician has assessed yet")
    args = parser.parse_args()

    db = SessionLocal()
    rows = []
    try:
        forms = db.query(m.ScreeningForm).order_by(m.ScreeningForm.submission_date).all()
        for f in forms:
            assessment = f.clinical_assessments[0] if f.clinical_assessments else None
            if assessment is None and not args.include_unlabeled:
                continue
            answers = json.loads(f.responses)
            row = {"patient_key": patient_key(f.mother_id)}
            row.update({k: answers.get(k) for k in FORM_FIELDS})
            row["clinical_label"] = assessment.risk_level.value if assessment else ""
            pred = f.prediction
            ml = (pred.ml_risk_level or pred.risk_level) if pred else None
            row["ml_prediction"] = ml.value if ml else ""
            row["facility_id"] = f.mother.facility_id
            row["submission_month"] = f.submission_date.strftime("%Y-%m")
            rows.append(row)
    finally:
        db.close()

    fieldnames = (["patient_key"] + FORM_FIELDS +
                  ["clinical_label", "ml_prediction", "facility_id", "submission_month"])
    with open(args.out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    labeled = sum(1 for r in rows if r["clinical_label"])
    print(f"Wrote {len(rows)} rows ({labeled} with a clinician label) to {args.out}")
    if labeled < 200:
        print("Note: fewer than ~200 clinician-labeled rows is too few to retrain reliably.")


if __name__ == "__main__":
    main()
