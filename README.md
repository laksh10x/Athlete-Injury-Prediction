# Athlete Injury Prediction

This repository now contains a reproducible version of the athlete injury prediction work shown in the project presentation, plus a stronger comparison pipeline for model selection and safer early-warning analysis.

## Project Goal

The original classroom goal was to replicate an SVM-based injury prediction pipeline inspired by:

Li et al. (2024). *A Big Data Approach to Forecast Injuries in Professional Sports Using Support Vector Machine*.  
*Mobile Networks and Applications*, Springer.

The repo now does two things:

1. Reproduces the presentation baseline exactly enough to match the reported findings.
2. Compares that baseline against stronger alternatives so the project can report both the most accurate model and the safest warning-oriented model.

## Dataset

- File: `data/collegiate_athlete_injury_dataset.csv`
- Samples: `200`
- Columns: `17`
- Injury cases: `14`
- Non-injury cases: `186`
- Holdout split used in the presentation: `70% train / 15% validation / 15% test`

## Implemented Pipelines

### 1. Baseline SVM Replication
- Drops `Athlete_ID`, `Gender`, and `Position`
- Standardizes numeric features
- Uses Recursive Feature Elimination (`RFE`) with a linear SVM
- Keeps `10` features
- Trains an `RBF` kernel SVM

### 2. Random Forest Comparison
- Uses the same numeric baseline feature set
- Applies `class_weight="balanced"` because the injury class is rare
- Produces feature-importance rankings for interpretation

### 3. Recall-First Threshold Rule
- Uses the baseline SVM probabilities
- Lowers the decision threshold to `0.085`
- Replicates the presentation-style early-warning idea by catching both injury cases while allowing a few false alarms

### 4. Logistic Extension
- Keeps all useful features except `Athlete_ID`
- One-hot encodes `Gender` and `Position`
- Uses balanced logistic regression
- Acts as the strongest safety-oriented extension in this repo

## Best Verified Results

### Holdout test split

| Model | Accuracy | Precision | Recall | F1 | Main takeaway |
|---|---:|---:|---:|---:|---|
| Baseline SVM + RFE10 | 0.9667 | 1.00 | 0.50 | 0.6667 | Best pure accuracy, but misses 1 of 2 injuries |
| Random Forest (balanced) | 0.9667 | 1.00 | 0.50 | 0.6667 | Matches SVM accuracy and gives feature importance |
| Logistic extension (all features) | 0.9333 | 0.50 | 1.00 | 0.6667 | Best safer model on the fixed test split |
| SVM threshold rule (0.085) | 0.9000 | 0.40 | 1.00 | 0.5714 | Replicates the recall-first warning idea from the presentation |

### Repeated cross-validation summary

Repeated `5x10` stratified cross-validation on the full dataset shows:

- `random_forest_balanced` has the highest mean accuracy: `0.9560`
- `logistic_extension_all_features` has the best overall balance between accuracy and injury recovery:
  - mean accuracy: `0.9435`
  - mean balanced accuracy: `0.8588`
  - mean recall: `0.7600`

In short:

- If the report needs the **most accurate verified model**, use **Random Forest** and the baseline **SVM** holdout tie.
- If the report needs the **strongest safety-oriented model**, use the **logistic extension** or the **threshold rule**.

## Repository Structure

```text
Athlete-Injury-Prediction/
|-- data/
|   `-- collegiate_athlete_injury_dataset.csv
|-- notebook/
|   |-- data_processing.ipynb
|   `-- svm_injury_prediction.ipynb
|-- results/
|   |-- cross_validation_summary.csv
|   |-- experiment_summary.json
|   |-- holdout_leaderboard.csv
|   |-- random_forest_feature_importance.csv
|   |-- selected_features.json
|   `-- figures/
|       |-- baseline_svm_confusion_matrix.png
|       |-- logistic_extension_confusion_matrix.png
|       `-- random_forest_feature_importance.png
|-- scripts/
|   `-- run_experiments.py
|-- src/
|   `-- athlete_injury_prediction/
|       |-- __init__.py
|       `-- experiment.py
|-- tests/
|   `-- test_pipeline.py
`-- requirements.txt
```

## How To Run

Install the dependencies:

```bash
pip install -r requirements.txt
```

Run the full experiment suite:

```bash
python scripts/run_experiments.py
```

Run the tests:

```bash
python -m unittest discover -s tests -v
```

## Saved Outputs

The experiment runner writes:

- `results/holdout_leaderboard.csv`
- `results/cross_validation_summary.csv`
- `results/experiment_summary.json`
- `results/random_forest_feature_importance.csv`
- `results/selected_features.json`
- the confusion-matrix and feature-importance figures under `results/figures/`

