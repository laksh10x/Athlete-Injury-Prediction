from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd


EXPECTED_HOLDOUT = {
    "baseline_svm_rbf_rfe10": {
        "accuracy": 0.9667,
        "precision": 1.00,
        "recall": 0.50,
    },
    "random_forest_balanced": {
        "accuracy": 0.9667,
        "precision": 1.00,
        "recall": 0.50,
    },
    "logistic_extension_all_features": {
        "accuracy": 0.9333,
        "precision": 0.50,
        "recall": 1.00,
    },
    "baseline_svm_threshold_rule_0_085": {
        "accuracy": 0.9000,
        "precision": 0.40,
        "recall": 1.00,
    },
}


EXPECTED_CV = {
    "random_forest_balanced": {
        "accuracy": 0.9560,
    },
    "logistic_extension_all_features": {
        "accuracy": 0.9435,
        "balanced_accuracy": 0.8588,
        "recall": 0.7600,
    },
}


def assert_close(actual: float, expected: float, label: str, tol: float = 1e-4) -> None:
    if not math.isclose(actual, expected, rel_tol=tol, abs_tol=tol):
        raise AssertionError(f"{label}: expected {expected:.4f}, got {actual:.4f}")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    results_dir = repo_root / "results"
    summary_path = results_dir / "experiment_summary.json"
    holdout_path = results_dir / "holdout_leaderboard.csv"
    cv_path = results_dir / "cross_validation_summary.csv"

    missing = [path for path in [summary_path, holdout_path, cv_path] if not path.exists()]
    if missing:
        print("Missing required result files:")
        for path in missing:
            print(f"  - {path}")
        print("Run `python scripts/run_experiments.py` first.")
        return 1

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    holdout = pd.read_csv(holdout_path).set_index("model")
    cv = pd.read_csv(cv_path).set_index("model")

    print("Checking dataset facts...")
    shape = tuple(summary["dataset"]["shape"])
    injury_count = int(summary["dataset"]["injury_count"])
    if shape != (200, 17):
        raise AssertionError(f"Dataset shape mismatch: expected (200, 17), got {shape}")
    if injury_count != 14:
        raise AssertionError(f"Injury count mismatch: expected 14, got {injury_count}")
    print("PASS dataset shape = (200, 17)")
    print("PASS injury count = 14")

    print("\nChecking holdout leaderboard...")
    for model_name, expected_metrics in EXPECTED_HOLDOUT.items():
        row = holdout.loc[model_name]
        for metric_name, expected_value in expected_metrics.items():
            actual_value = float(row[metric_name])
            assert_close(actual_value, expected_value, f"{model_name} {metric_name}")
        print(
            f"PASS {model_name}: "
            f"accuracy={row['accuracy']:.4f}, precision={row['precision']:.4f}, recall={row['recall']:.4f}"
        )

    print("\nChecking paper-ready baseline details...")
    baseline_test = summary["baseline_svm"]["test"]
    if baseline_test["confusion_matrix"] != [[28, 0], [1, 1]]:
        raise AssertionError(
            "Baseline SVM confusion matrix mismatch: "
            f"expected [[28, 0], [1, 1]], got {baseline_test['confusion_matrix']}"
        )
    print("PASS baseline SVM confusion matrix = [[28, 0], [1, 1]]")

    threshold_rule = summary["baseline_svm"]["threshold_rule"]
    logistic_test = summary["logistic_extension"]["test"]
    if threshold_rule["confusion_matrix"] != [[25, 3], [0, 2]]:
        raise AssertionError(
            "Threshold-rule confusion matrix mismatch: "
            f"expected [[25, 3], [0, 2]], got {threshold_rule['confusion_matrix']}"
        )
    if logistic_test["confusion_matrix"] != [[26, 2], [0, 2]]:
        raise AssertionError(
            "Logistic-extension confusion matrix mismatch: "
            f"expected [[26, 2], [0, 2]], got {logistic_test['confusion_matrix']}"
        )
    print("PASS threshold-rule confusion matrix = [[25, 3], [0, 2]]")
    print("PASS logistic-extension confusion matrix = [[26, 2], [0, 2]]")

    print("\nChecking cross-validation summary...")
    for model_name, expected_metrics in EXPECTED_CV.items():
        row = cv.loc[model_name]
        for metric_name, expected_value in expected_metrics.items():
            actual_value = float(row[metric_name])
            assert_close(actual_value, expected_value, f"{model_name} {metric_name}", tol=1e-3)
        shown = ", ".join(f"{metric}={row[metric]:.4f}" for metric in expected_metrics)
        print(f"PASS {model_name}: {shown}")

    best_accuracy_model = cv["accuracy"].astype(float).idxmax()
    if best_accuracy_model != "random_forest_balanced":
        raise AssertionError(
            f"Best cross-validation accuracy should be random_forest_balanced, got {best_accuracy_model}"
        )
    print("PASS cross-validation accuracy winner = random_forest_balanced")

    print("\nAll demo result checks passed.")
    print(f"Results directory: {results_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
