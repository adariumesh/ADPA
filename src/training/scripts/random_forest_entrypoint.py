"""Default SageMaker entry point for sklearn RandomForest training."""

import argparse
import json
import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


def _load_training_data(training_dir: Path) -> pd.DataFrame:
    csv_files = sorted(training_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {training_dir}")
    frames = [pd.read_csv(path) for path in csv_files]
    return pd.concat(frames, ignore_index=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-column", "--target_column", dest="target_column", type=str, default="target")
    parser.add_argument("--test-size", "--test_size", dest="test_size", type=float, default=0.2)
    parser.add_argument("--random-state", "--random_state", dest="random_state", type=int, default=42)
    parser.add_argument("--n-estimators", "--n_estimators", dest="n_estimators", type=int, default=100)
    parser.add_argument("--max-depth", "--max_depth", dest="max_depth", type=int, default=None)
    parser.add_argument("--min-samples-split", "--min_samples_split", dest="min_samples_split", type=int, default=2)
    parser.add_argument("--min-samples-leaf", "--min_samples_leaf", dest="min_samples_leaf", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    training_dir = Path(os.environ["SM_CHANNEL_TRAINING"])
    model_dir = Path(os.environ["SM_MODEL_DIR"])
    output_dir = Path(os.environ.get("SM_OUTPUT_DATA_DIR", "/opt/ml/output"))

    df = _load_training_data(training_dir)
    if args.target_column not in df.columns:
        raise ValueError(f"Target column '{args.target_column}' not found in dataset")

    X = df.drop(columns=[args.target_column])
    y = df[args.target_column]

    unique_classes = y.unique()
    stratify_labels = None
    if len(unique_classes) > 1:
        expected_test = max(1, int(round(len(y) * args.test_size)))
        if expected_test >= len(unique_classes):
            stratify_labels = y
        else:
            print(
                f"[ADPA][Warning] dataset too small for stratified split (test samples={expected_test}, classes={len(unique_classes)}) - falling back to random split"
            )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=stratify_labels,
    )

    clf = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_split=args.min_samples_split,
        min_samples_leaf=args.min_samples_leaf,
        random_state=args.random_state,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    report = classification_report(y_test, preds, output_dict=True)

    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, model_dir / "model.joblib")

    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"
    with metrics_path.open("w") as fp:
        json.dump({"accuracy": acc, "classification_report": report}, fp)

    print(f"Training completed. Accuracy: {acc:.4f}")


if __name__ == "__main__":
    main()
