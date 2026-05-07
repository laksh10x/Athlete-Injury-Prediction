from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

import sys

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from athlete_injury_prediction.experiment import load_dataset, run_holdout_experiments


class AthletePipelineTests(unittest.TestCase):
    def test_dataset_shape_and_class_balance(self):
        df = load_dataset(REPO_ROOT)
        self.assertEqual(df.shape, (200, 17))
        self.assertEqual(int(df["Injury_Indicator"].sum()), 14)

    def test_baseline_svm_reproduces_presentation_holdout(self):
        results = run_holdout_experiments(REPO_ROOT)
        baseline_test = results["baseline_svm"]["test"]
        self.assertEqual(baseline_test["confusion_matrix"], [[28, 0], [1, 1]])
        self.assertAlmostEqual(baseline_test["accuracy"], 29 / 30, places=6)
        self.assertAlmostEqual(baseline_test["recall"], 0.5, places=6)

    def test_safety_models_recover_all_injury_cases(self):
        results = run_holdout_experiments(REPO_ROOT)
        threshold_rule = results["baseline_svm"]["threshold_rule"]
        logistic_extension = results["logistic_extension"]["test"]
        self.assertAlmostEqual(threshold_rule["recall"], 1.0, places=6)
        self.assertAlmostEqual(logistic_extension["recall"], 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
