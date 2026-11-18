"""
Cross-validated comparison of the four classifiers, with two ways of handling class imbalance:
SMOTE (applied inside each training fold only) versus class weights. Implements the model-selection
protocol in Section 3.4.6 of the proposal.

    python3 cv_imbalance_comparison.py        # writes ../trained_model/cv_results.json

Data preparation mirrors the notebook (Sections 1-4): same renaming, value normalisation, ordinal
coding, tercile labels and group-aware 80/20 split; then 5-fold StratifiedGroupKFold on the
TRAINING part only, so the held-out test rows never influence the choice.
"""
import json
import os
import warnings

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
SEED = 42
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "post_natal_data.csv")

RENAME = {"Age": "age_bracket", "Feeling sad or Tearful": "feeling_sad", "Irritable towards baby & partner": "irritable",
          "Trouble sleeping at night": "trouble_sleeping", "Problems concentrating or making decision": "trouble_concentrating",
          "Overeating or loss of appetite": "appetite_changes", "Feeling anxious": "feeling_anxious",
          "Feeling of guilt": "feeling_guilty", "Problems of bonding with baby": "bonding_difficulty",
          "Suicide attempt": "self_harm_thoughts"}
SYMPTOMS = ["feeling_sad", "irritable", "trouble_sleeping", "trouble_concentrating", "appetite_changes",
            "feeling_anxious", "feeling_guilty", "bonding_difficulty"]
NORMALISE = {"Two or more days a week": "Yes", "Often": "Yes", "Not at all": "No", "Maybe": "Sometimes",
             "Not interested to say": "Sometimes"}
ORD = {"No": 0, "Sometimes": 1, "Yes": 2}
AGES = ["25-30", "30-35", "35-40", "40-45", "45-50"]


def load():
    df = pd.read_csv(DATA).drop(columns=["Timestamp"], errors="ignore").rename(columns=RENAME).dropna().reset_index(drop=True)
    cols = SYMPTOMS + ["self_harm_thoughts"]
    for c in cols:
        df[c] = df[c].replace(NORMALISE)
    df["pattern"] = df[cols + ["age_bracket"]].astype(str).agg("|".join, axis=1)
    for c in SYMPTOMS:
        df[c] = df[c].map(ORD)
    df["age_bracket"] = df["age_bracket"].map({a: i for i, a in enumerate(AGES)})
    score = df[SYMPTOMS].sum(axis=1)
    q1, q2 = score.quantile([1 / 3, 2 / 3])
    df["risk"] = np.where(score <= q1, "low", np.where(score <= q2, "medium", "high"))
    return df


def models():
    return {
        "Logistic Regression": lambda: LogisticRegression(max_iter=1000, random_state=SEED),
        "SVM": lambda: SVC(random_state=SEED),
        "Random Forest": lambda: RandomForestClassifier(n_estimators=200, random_state=SEED),
        "XGBoost": lambda: XGBClassifier(n_estimators=200, eval_metric="mlogloss", random_state=SEED),
    }


def fit_predict(make, strategy, Xtr, ytr, Xte):
    if strategy == "smote":
        Xb, yb = SMOTE(random_state=SEED).fit_resample(Xtr, ytr)   # resampling sees training rows only
        return make().fit(Xb, yb).predict(Xte)
    w = compute_sample_weight("balanced", ytr)                       # class weights
    m = make()
    try:
        m.fit(Xtr, ytr, sample_weight=w)
    except TypeError:
        m.fit(Xtr, ytr)
    return m.predict(Xte)


def main():
    df = load()
    feats = SYMPTOMS + ["age_bracket"]
    y = LabelEncoder().fit_transform(df["risk"])
    X, groups = df[feats].values, df["pattern"].values

    tr, te = next(StratifiedGroupKFold(5, shuffle=True, random_state=SEED).split(X, y, groups))
    Xtr, ytr, gtr = X[tr], y[tr], groups[tr]
    print(f"train {len(tr)} rows, held-out test {len(te)} rows (never used here)")

    cv = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)
    results = []
    for name, make in models().items():
        for strategy in ("smote", "class_weights"):
            scores = [f1_score(ytr[v], fit_predict(make, strategy, Xtr[t], ytr[t], Xtr[v]), average="macro")
                      for t, v in cv.split(Xtr, ytr, groups=gtr)]
            results.append({"model": name, "imbalance": strategy, "mean_macro_f1": round(float(np.mean(scores)), 4),
                            "std": round(float(np.std(scores)), 4)})
            print(f"{name:20s} {strategy:14s} macro F1 {np.mean(scores):.4f} +/- {np.std(scores):.4f}")

    # Protocol: per model, class weights win unless SMOTE is better by at least 0.01.
    for name in models():
        s = next(r for r in results if r["model"] == name and r["imbalance"] == "smote")["mean_macro_f1"]
        c = next(r for r in results if r["model"] == name and r["imbalance"] == "class_weights")["mean_macro_f1"]
        print(f"{name:20s} -> {'SMOTE' if s - c >= 0.01 else 'class weights'} (diff {s - c:+.4f})")
    with open(os.path.join(HERE, "..", "trained_model", "cv_results.json"), "w") as fh:
        json.dump(results, fh, indent=2)


if __name__ == "__main__":
    main()
