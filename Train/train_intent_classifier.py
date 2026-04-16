from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple
import json
import shutil
from datetime import datetime
import time

import joblib
import numpy as np
import pandas as pd
from tqdm import tqdm

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from sentence_transformers import SentenceTransformer

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Dataset dans Train/
DATA_PATH = SCRIPT_DIR / "intent_dataset.csv"

# Modèles sauvegardés là où ton backend peut les relire
MODEL_DIR = PROJECT_ROOT / "backend" / "ai" / "agent" / "routing" / "models" / "intent_router"

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TEST_SIZE = 0.2
MIN_SAMPLES_PER_CLASS = 5
RANDOM_STATE = 42
ALLOWED_LABELS = {"price", "stats", "compare", "screener", "chat"}
EMBEDDING_BATCH_SIZE = 32


def load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset introuvable: {path}")

    df = pd.read_csv(path)

    required = {"text", "intent"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans le dataset: {sorted(missing)}")

    df = df.dropna(subset=["text", "intent"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df["intent"] = df["intent"].astype(str).str.strip().str.lower()

    df = df[df["text"] != ""].copy()
    df = df[df["intent"].isin(ALLOWED_LABELS)].copy()

    if df.empty:
        raise ValueError("Le dataset est vide après nettoyage.")

    counts = df["intent"].value_counts()
    too_small = counts[counts < MIN_SAMPLES_PER_CLASS]
    if not too_small.empty:
        raise ValueError(
            "Certaines classes n'ont pas assez d'exemples pour un split stratifié: "
            + ", ".join(f"{label}={count}" for label, count in too_small.items())
        )

    return df.reset_index(drop=True)


def build_embeddings(texts: List[str], model_name: str, batch_size: int = EMBEDDING_BATCH_SIZE) -> np.ndarray:
    print(f"\nChargement du modèle d'embedding: {model_name}")
    model = SentenceTransformer(model_name)

    print(f"Construction des embeddings en batch_size={batch_size}...")
    all_embeddings: list[np.ndarray] = []

    for start_idx in tqdm(
        range(0, len(texts), batch_size),
        desc="Embedding batches",
        unit="batch",
    ):
        batch_texts = texts[start_idx : start_idx + batch_size]
        batch_embeddings = model.encode(
            batch_texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        all_embeddings.append(np.asarray(batch_embeddings))

    if not all_embeddings:
        raise ValueError("Aucun embedding généré.")

    return np.vstack(all_embeddings)


def split_data(
    X: np.ndarray,
    y: np.ndarray,
    df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, pd.DataFrame, pd.DataFrame]:
    X_train, X_test, y_train, y_test, df_train, df_test = train_test_split(
        X,
        y,
        df,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    return (
        X_train,
        X_test,
        y_train,
        y_test,
        df_train.reset_index(drop=True),
        df_test.reset_index(drop=True),
    )


def train_classifier(X_train: np.ndarray, y_train: np.ndarray) -> LogisticRegression:
    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        solver="lbfgs",
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    return clf


def backup_existing_artifacts(output_dir: Path) -> Path | None:
    existing_files = [
        output_dir / "intent_classifier.joblib",
        output_dir / "label_encoder.joblib",
        output_dir / "metadata.json",
        output_dir / "misclassified_examples.csv",
        output_dir / "confusion_matrix.csv",
    ]

    if not any(path.exists() for path in existing_files):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = output_dir / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    for path in existing_files:
        if path.exists():
            shutil.copy2(path, backup_dir / path.name)

    return backup_dir


def save_artifacts(
    clf: LogisticRegression,
    le: LabelEncoder,
    metadata: dict,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(clf, output_dir / "intent_classifier.joblib")
    joblib.dump(le, output_dir / "label_encoder.joblib")
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_errors_report(
    df_test: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    le: LabelEncoder,
    output_dir: Path,
) -> None:
    true_labels = le.inverse_transform(y_true)
    pred_labels = le.inverse_transform(y_pred)

    report_df = df_test.copy()
    report_df["true_intent"] = true_labels
    report_df["pred_intent"] = pred_labels
    report_df["is_correct"] = report_df["true_intent"] == report_df["pred_intent"]

    errors_df = report_df[~report_df["is_correct"]].copy()
    errors_df.to_csv(output_dir / "misclassified_examples.csv", index=False, encoding="utf-8")


def save_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    le: LabelEncoder,
    output_dir: Path,
) -> None:
    cm = confusion_matrix(y_true, y_pred)
    cm_df = pd.DataFrame(cm, index=le.classes_, columns=le.classes_)
    cm_df.index.name = "true_label"
    cm_df.to_csv(output_dir / "confusion_matrix.csv", encoding="utf-8")


def main() -> None:
    total_start = time.perf_counter()

    print(f"Script dir   : {SCRIPT_DIR}")
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Dataset path : {DATA_PATH}")
    print(f"Model dir    : {MODEL_DIR}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    pipeline_steps = [
        "load_dataset",
        "build_embeddings",
        "encode_labels",
        "split_data",
        "train_model",
        "evaluate",
        "backup_old_artifacts",
        "save_artifacts",
    ]

    step_bar = tqdm(pipeline_steps, desc="Pipeline", unit="step")

    for step in step_bar:
        if step == "load_dataset":
            step_bar.set_postfix_str("lecture du dataset")
            print(f"\nChargement du dataset depuis: {DATA_PATH}")
            df = load_dataset(DATA_PATH)

            print(f"Nombre total d'exemples: {len(df)}")
            print("\nRépartition des labels:")
            print(df["intent"].value_counts())

        elif step == "build_embeddings":
            step_bar.set_postfix_str("embeddings")
            X = build_embeddings(df["text"].tolist(), EMBEDDING_MODEL_NAME)

        elif step == "encode_labels":
            step_bar.set_postfix_str("encodage labels")
            le = LabelEncoder()
            y = le.fit_transform(df["intent"].tolist())

        elif step == "split_data":
            step_bar.set_postfix_str("split train/test")
            X_train, X_test, y_train, y_test, df_train, df_test = split_data(X, y, df)

        elif step == "train_model":
            step_bar.set_postfix_str("entraînement")
            print("\nEntraînement du classifieur...")
            clf = train_classifier(X_train, y_train)

        elif step == "evaluate":
            step_bar.set_postfix_str("évaluation")
            print("Évaluation...")
            y_pred = clf.predict(X_test)

            acc = accuracy_score(y_test, y_pred)
            macro_f1 = f1_score(y_test, y_pred, average="macro")
            weighted_f1 = f1_score(y_test, y_pred, average="weighted")

            print(f"\nAccuracy   : {acc:.4f}")
            print(f"Macro F1   : {macro_f1:.4f}")
            print(f"Weighted F1: {weighted_f1:.4f}")

            print("\nClassification report:\n")
            print(classification_report(y_test, y_pred, target_names=le.classes_))

        elif step == "backup_old_artifacts":
            step_bar.set_postfix_str("backup")
            backup_dir = backup_existing_artifacts(MODEL_DIR)
            if backup_dir is not None:
                print(f"\nBackup des anciens artefacts créé dans: {backup_dir}")

        elif step == "save_artifacts":
            step_bar.set_postfix_str("sauvegarde")
            metadata = {
                "embedding_model_name": EMBEDDING_MODEL_NAME,
                "embedding_batch_size": EMBEDDING_BATCH_SIZE,
                "n_samples": int(len(df)),
                "n_train_samples": int(len(df_train)),
                "n_test_samples": int(len(df_test)),
                "labels": list(le.classes_),
                "label_distribution": df["intent"].value_counts().to_dict(),
                "accuracy": float(acc),
                "macro_f1": float(macro_f1),
                "weighted_f1": float(weighted_f1),
                "test_size": TEST_SIZE,
                "random_state": RANDOM_STATE,
                "min_samples_per_class": MIN_SAMPLES_PER_CLASS,
                "model_type": "LogisticRegression",
                "model_params": {
                    "max_iter": 2000,
                    "class_weight": "balanced",
                    "random_state": RANDOM_STATE,
                    "solver": "lbfgs",
                },
                "data_path": str(DATA_PATH),
                "model_dir": str(MODEL_DIR),
                "trained_at": datetime.now().isoformat(),
            }

            save_artifacts(clf=clf, le=le, metadata=metadata, output_dir=MODEL_DIR)
            save_errors_report(
                df_test=df_test,
                y_true=y_test,
                y_pred=y_pred,
                le=le,
                output_dir=MODEL_DIR,
            )
            save_confusion_matrix(
                y_true=y_test,
                y_pred=y_pred,
                le=le,
                output_dir=MODEL_DIR,
            )

    total_duration = time.perf_counter() - total_start

    print(f"\nArtifacts sauvegardés dans: {MODEL_DIR}")
    print(f"- {MODEL_DIR / 'intent_classifier.joblib'}")
    print(f"- {MODEL_DIR / 'label_encoder.joblib'}")
    print(f"- {MODEL_DIR / 'metadata.json'}")
    print(f"- {MODEL_DIR / 'misclassified_examples.csv'}")
    print(f"- {MODEL_DIR / 'confusion_matrix.csv'}")
    print(f"\nTemps total: {total_duration:.2f}s")


if __name__ == "__main__":
    main()
