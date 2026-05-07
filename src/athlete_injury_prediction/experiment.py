from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    make_scorer,
    precision_score,
    recall_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC


RANDOM_STATE = 42
TARGET_COLUMN = "Injury_Indicator"
ID_COLUMN = "Athlete_ID"
BASELINE_DROP_COLUMNS = [TARGET_COLUMN, ID_COLUMN, "Gender", "Position"]
DEFAULT_DATASET_GLOB = "*injury*.csv"
THRESHOLD_RULE = 0.085


@dataclass
class SplitData:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame


class RFEClassifier(BaseEstimator, ClassifierMixin):
    """Reusable RFE + estimator wrapper for cross-validation and holdout runs."""

    def __init__(self, estimator: BaseEstimator, n_features_to_select: int = 10, scale: bool = True):
        self.estimator = estimator
        self.n_features_to_select = n_features_to_select
        self.scale = scale

    def fit(self, X: pd.DataFrame | np.ndarray, y: pd.Series | np.ndarray):
        self.feature_names_in_ = list(X.columns) if isinstance(X, pd.DataFrame) else None
        X_values = X.values if isinstance(X, pd.DataFrame) else X
        self.scaler_ = StandardScaler() if self.scale else None
        X_scaled = self.scaler_.fit_transform(X_values) if self.scaler_ else X_values
        self.selector_ = RFE(SVC(kernel="linear"), n_features_to_select=self.n_features_to_select)
        X_selected = self.selector_.fit_transform(X_scaled, y)
        self.estimator_ = clone(self.estimator)
        self.estimator_.fit(X_selected, y)
        return self

    def _transform(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        X_values = X.values if isinstance(X, pd.DataFrame) else X
        X_scaled = self.scaler_.transform(X_values) if self.scaler_ else X_values
        return self.selector_.transform(X_scaled)

    def predict(self, X: pd.DataFrame | np.ndarray):
        return self.estimator_.predict(self._transform(X))

    def predict_proba(self, X: pd.DataFrame | np.ndarray):
        return self.estimator_.predict_proba(self._transform(X))


def find_dataset_path(repo_root: Path) -> Path:
    candidates = sorted((repo_root / "data").glob(DEFAULT_DATASET_GLOB))
    if not candidates:
        raise FileNotFoundError("Could not find the athlete injury dataset in the data directory.")
    return candidates[0]


def load_dataset(repo_root: Path) -> pd.DataFrame:
    dataset_path = find_dataset_path(repo_root)
    df = pd.read_csv(dataset_path)
    df.columns = [column.strip() for column in df.columns]
    return df


def split_dataset(df: pd.DataFrame) -> SplitData:
    train_idx, temp_idx, _, temp_y = train_test_split(
        df.index,
        df[TARGET_COLUMN],
        test_size=0.30,
        random_state=RANDOM_STATE,
        stratify=df[TARGET_COLUMN],
    )
    val_idx, test_idx, _, _ = train_test_split(
        temp_idx,
        temp_y,
        test_size=0.50,
        random_state=RANDOM_STATE,
        stratify=temp_y,
    )
    return SplitData(
        train=df.loc[train_idx].copy(),
        val=df.loc[val_idx].copy(),
        test=df.loc[test_idx].copy(),
    )


def get_numeric_baseline_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=BASELINE_DROP_COLUMNS)


def get_all_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=[TARGET_COLUMN, ID_COLUMN])


def metric_dict(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": cm.tolist(),
        "classification_report": classification_report(y_true, y_pred, output_dict=True, zero_division=0),
    }


def run_baseline_svm(split_data: SplitData) -> dict[str, Any]:
    X_train = get_numeric_baseline_frame(split_data.train)
    X_val = get_numeric_baseline_frame(split_data.val)
    X_test = get_numeric_baseline_frame(split_data.test)
    y_train = split_data.train[TARGET_COLUMN]
    y_val = split_data.val[TARGET_COLUMN]
    y_test = split_data.test[TARGET_COLUMN]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    selector = RFE(SVC(kernel="linear"), n_features_to_select=10)
    X_train_rfe = selector.fit_transform(X_train_scaled, y_train)
    X_val_rfe = selector.transform(X_val_scaled)
    X_test_rfe = selector.transform(X_test_scaled)
    selected_features = [name for name, keep in zip(X_train.columns, selector.support_) if keep]

    model = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True, random_state=RANDOM_STATE)
    model.fit(X_train_rfe, y_train)

    val_pred = model.predict(X_val_rfe)
    test_pred = model.predict(X_test_rfe)
    test_proba = model.predict_proba(X_test_rfe)[:, 1]

    threshold_pred = (test_proba >= THRESHOLD_RULE).astype(int)

    return {
        "model_name": "baseline_svm_rbf_rfe10",
        "selected_features": selected_features,
        "validation": metric_dict(y_val, val_pred),
        "test": metric_dict(y_test, test_pred),
        "threshold_rule": {
            "threshold": THRESHOLD_RULE,
            **metric_dict(y_test, threshold_pred),
        },
        "test_probabilities": test_proba.tolist(),
    }


def run_random_forest(split_data: SplitData) -> dict[str, Any]:
    X_train = get_numeric_baseline_frame(split_data.train)
    X_val = get_numeric_baseline_frame(split_data.val)
    X_test = get_numeric_baseline_frame(split_data.test)
    y_train = split_data.train[TARGET_COLUMN]
    y_val = split_data.val[TARGET_COLUMN]
    y_test = split_data.test[TARGET_COLUMN]

    model = RandomForestClassifier(
        n_estimators=200,
        random_state=RANDOM_STATE,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)
    importances = sorted(
        zip(X_train.columns, model.feature_importances_),
        key=lambda item: item[1],
        reverse=True,
    )
    return {
        "model_name": "random_forest_balanced",
        "validation": metric_dict(y_val, val_pred),
        "test": metric_dict(y_test, test_pred),
        "feature_importances": [{"feature": name, "importance": float(score)} for name, score in importances],
    }


def run_logistic_extension(split_data: SplitData) -> dict[str, Any]:
    X_train = get_all_feature_frame(split_data.train)
    X_val = get_all_feature_frame(split_data.val)
    X_test = get_all_feature_frame(split_data.test)
    y_train = split_data.train[TARGET_COLUMN]
    y_val = split_data.val[TARGET_COLUMN]
    y_test = split_data.test[TARGET_COLUMN]

    numeric_columns = [column for column in X_train.columns if X_train[column].dtype != "object"]
    categorical_columns = [column for column in X_train.columns if X_train[column].dtype == "object"]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            ),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=5000, class_weight="balanced", C=5.0)),
        ]
    )
    model.fit(X_train, y_train)

    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)
    return {
        "model_name": "logistic_extension_all_features",
        "validation": metric_dict(y_val, val_pred),
        "test": metric_dict(y_test, test_pred),
        "feature_mode": "numeric + one-hot encoded categorical features",
    }


def run_holdout_experiments(repo_root: Path) -> dict[str, Any]:
    df = load_dataset(repo_root)
    split_data = split_dataset(df)

    baseline = run_baseline_svm(split_data)
    random_forest = run_random_forest(split_data)
    logistic_extension = run_logistic_extension(split_data)

    return {
        "dataset": {
            "path": str(find_dataset_path(repo_root)),
            "shape": list(df.shape),
            "injury_count": int(df[TARGET_COLUMN].sum()),
            "non_injury_count": int((df[TARGET_COLUMN] == 0).sum()),
        },
        "split_sizes": {
            "train": int(split_data.train.shape[0]),
            "validation": int(split_data.val.shape[0]),
            "test": int(split_data.test.shape[0]),
        },
        "baseline_svm": baseline,
        "random_forest": random_forest,
        "logistic_extension": logistic_extension,
    }


def cross_validate_models(repo_root: Path) -> pd.DataFrame:
    df = load_dataset(repo_root)
    X_baseline = get_numeric_baseline_frame(df)
    X_all = get_all_feature_frame(df)
    y = df[TARGET_COLUMN]

    numeric_columns = [column for column in X_all.columns if X_all[column].dtype != "object"]
    categorical_columns = [column for column in X_all.columns if X_all[column].dtype == "object"]

    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=RANDOM_STATE)
    scoring = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "precision": make_scorer(precision_score, zero_division=0),
        "recall": make_scorer(recall_score, zero_division=0),
        "f1": make_scorer(f1_score, zero_division=0),
    }

    all_feature_pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                ColumnTransformer(
                    transformers=[
                        (
                            "num",
                            Pipeline(
                                steps=[
                                    ("imputer", SimpleImputer(strategy="median")),
                                    ("scaler", StandardScaler()),
                                ]
                            ),
                            numeric_columns,
                        ),
                        (
                            "cat",
                            Pipeline(
                                steps=[
                                    ("imputer", SimpleImputer(strategy="most_frequent")),
                                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                                ]
                            ),
                            categorical_columns,
                        ),
                    ]
                ),
            ),
            ("classifier", LogisticRegression(max_iter=5000, class_weight="balanced", C=5.0)),
        ]
    )

    models = {
        "baseline_svm_rbf_rfe10": (RFEClassifier(SVC(kernel="rbf", C=1.0, gamma="scale", probability=True, random_state=RANDOM_STATE), n_features_to_select=10), X_baseline),
        "random_forest_balanced": (RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE, class_weight="balanced"), X_baseline),
        "logistic_extension_rfe8": (RFEClassifier(LogisticRegression(max_iter=5000, class_weight="balanced", C=1.0), n_features_to_select=8), X_baseline),
        "logistic_extension_all_features": (all_feature_pipeline, X_all),
    }

    rows: list[dict[str, Any]] = []
    for model_name, (model, frame) in models.items():
        scores = cross_validate(model, frame, y, cv=cv, scoring=scoring)
        row = {"model": model_name}
        for metric in scoring.keys():
            row[metric] = float(scores[f"test_{metric}"].mean())
            row[f"{metric}_std"] = float(scores[f"test_{metric}"].std())
        rows.append(row)

    return pd.DataFrame(rows).sort_values(["accuracy", "balanced_accuracy"], ascending=False).reset_index(drop=True)


def _plot_confusion_matrix(matrix: list[list[int]], title: str, out_path: Path) -> None:
    cm = np.array(matrix)
    fig, ax = plt.subplots(figsize=(3.5, 3.2), dpi=180)
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1], labels=["Pred 0", "Pred 1"])
    ax.set_yticks([0, 1], labels=["Actual 0", "Actual 1"])
    ax.set_title(title, fontsize=11)
    for row in range(cm.shape[0]):
        for col in range(cm.shape[1]):
            ax.text(col, row, str(cm[row, col]), ha="center", va="center", fontsize=12, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def _plot_feature_importance(importances: list[dict[str, Any]], title: str, out_path: Path) -> None:
    top = importances[:6]
    labels = [item["feature"] for item in reversed(top)]
    values = [item["importance"] for item in reversed(top)]
    fig, ax = plt.subplots(figsize=(5.5, 3.6), dpi=180)
    ax.barh(labels, values, color=["#18435A", "#1F6C7A", "#2C9F8E", "#70B04F", "#D9A21B", "#C70039"])
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Importance")
    ax.tick_params(axis="both", labelsize=9)
    plt.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def _leaderboard_frame(holdout: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {"model": "baseline_svm_rbf_rfe10", **{k: holdout["baseline_svm"]["test"][k] for k in ["accuracy", "balanced_accuracy", "precision", "recall", "f1"]}},
        {"model": "random_forest_balanced", **{k: holdout["random_forest"]["test"][k] for k in ["accuracy", "balanced_accuracy", "precision", "recall", "f1"]}},
        {"model": f"baseline_svm_threshold_rule_{str(THRESHOLD_RULE).replace('.', '_')}", **{k: holdout["baseline_svm"]["threshold_rule"][k] for k in ["accuracy", "balanced_accuracy", "precision", "recall", "f1"]}},
        {"model": "logistic_extension_all_features", **{k: holdout["logistic_extension"]["test"][k] for k in ["accuracy", "balanced_accuracy", "precision", "recall", "f1"]}},
    ]
    return pd.DataFrame(rows).sort_values(["accuracy", "balanced_accuracy"], ascending=False).reset_index(drop=True)


def save_results(repo_root: Path, holdout: dict[str, Any], cv_results: pd.DataFrame) -> dict[str, str]:
    results_dir = repo_root / "results"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(exist_ok=True)
    figures_dir.mkdir(exist_ok=True)

    leaderboard = _leaderboard_frame(holdout)
    leaderboard_path = results_dir / "holdout_leaderboard.csv"
    cv_path = results_dir / "cross_validation_summary.csv"
    holdout_json_path = results_dir / "experiment_summary.json"
    selected_features_path = results_dir / "selected_features.json"
    rf_importance_path = results_dir / "random_forest_feature_importance.csv"

    leaderboard.to_csv(leaderboard_path, index=False)
    cv_results.to_csv(cv_path, index=False)
    holdout_json_path.write_text(json.dumps(holdout, indent=2), encoding="utf-8")
    selected_features_path.write_text(
        json.dumps(
            {
                "baseline_svm_rfe10": holdout["baseline_svm"]["selected_features"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(holdout["random_forest"]["feature_importances"]).to_csv(rf_importance_path, index=False)

    _plot_confusion_matrix(
        holdout["baseline_svm"]["test"]["confusion_matrix"],
        "Baseline SVM Confusion Matrix",
        figures_dir / "baseline_svm_confusion_matrix.png",
    )
    _plot_confusion_matrix(
        holdout["logistic_extension"]["test"]["confusion_matrix"],
        "Logistic Extension Confusion Matrix",
        figures_dir / "logistic_extension_confusion_matrix.png",
    )
    _plot_feature_importance(
        holdout["random_forest"]["feature_importances"],
        "Random Forest Feature Importance",
        figures_dir / "random_forest_feature_importance.png",
    )

    return {
        "results_dir": str(results_dir),
        "leaderboard_csv": str(leaderboard_path),
        "cross_validation_csv": str(cv_path),
        "summary_json": str(holdout_json_path),
    }


def run_all_experiments(repo_root: Path) -> dict[str, Any]:
    holdout = run_holdout_experiments(repo_root)
    cv_results = cross_validate_models(repo_root)
    saved = save_results(repo_root, holdout, cv_results)
    return {"holdout": holdout, "cross_validation": cv_results.to_dict(orient="records"), "saved_files": saved}
