# Demo Guide

This guide is for the required project implementation demo on a fresh computer.

## Before You Start Recording

1. Use a computer you have not used for coding this project.
2. Sign in to your PSU account and Zoom.
3. Start the Zoom recording before you download the project.
4. Turn on screen sharing and webcam.
5. Keep the GitHub repo page, the README, and the terminal visible during the demo.

## What To Show In Order

### 1. Download the project from GitHub

You can use either option below:

- Option A: open the GitHub repo, click `Code`, then `Download ZIP`
- Option B: if Git is installed, run:

```powershell
git clone https://github.com/laksh10x/Athlete-Injury-Prediction.git
cd Athlete-Injury-Prediction
```

If you use the ZIP option:

```powershell
cd <path-to-extracted-folder>\Athlete-Injury-Prediction
```

### 2. Open the README and explain the repo

Show:

- project goal
- implemented models
- expected results
- how to run the project

### 3. Run the full demo script

From the repo root:

```powershell
.\run_demo.bat
```

If PowerShell asks for permission, allow it. The script will:

- create a fresh virtual environment
- install requirements
- run the experiments
- verify that the saved results match the paper
- run the unit tests

### 4. Show the generated results

Open these files after the script finishes:

- `results\holdout_leaderboard.csv`
- `results\cross_validation_summary.csv`
- `results\experiment_summary.json`
- `results\figures\baseline_svm_confusion_matrix.png`
- `results\figures\random_forest_feature_importance.png`

## What To Say During The Demo

### Recommended short explanation flow

1. `README.md`
   Explain the project goal, the dataset size, and the four modeling approaches.

2. `scripts\run_experiments.py`
   Explain that this is the main entry point. It loads the reusable experiment pipeline and runs the full project from code instead of from notebook cells.

3. `src\athlete_injury_prediction\experiment.py`
   Explain this file in sections:
   - data loading and preprocessing
   - baseline SVM pipeline
   - Random Forest comparison
   - logistic extension
   - threshold-rule evaluation
   - metric saving and figure generation

4. `tests\test_pipeline.py`
   Explain that the tests check the dataset facts and the main reported results, especially the baseline holdout confusion matrix and the safety-model recall.

### Key result lines to mention

- Baseline SVM holdout accuracy: `0.9667`
- Baseline SVM holdout recall: `0.50`
- Random Forest holdout accuracy: `0.9667`
- Logistic extension holdout recall: `1.00`
- Threshold rule holdout recall: `1.00`
- Best cross-validation accuracy: `random_forest_balanced` with about `0.956`

### Simple spoken interpretation

You can say:

> The baseline SVM and Random Forest had the best holdout accuracy, but they still missed one of the two injury cases. The logistic extension and the threshold rule were safer because they caught both injury cases. That is why the final paper does not judge the project by accuracy alone.

## Backup Commands

If the batch file does not run, use these commands one by one:

```powershell
py -3 -m venv .demo-venv
.\.demo-venv\Scripts\python.exe -m pip install --upgrade pip
.\.demo-venv\Scripts\python.exe -m pip install -r requirements.txt
.\.demo-venv\Scripts\python.exe scripts\run_experiments.py
.\.demo-venv\Scripts\python.exe scripts\verify_demo_results.py
.\.demo-venv\Scripts\python.exe -m unittest discover -s tests -v
```

If `py` is not available, replace it with `python`.

## Final Recording Checklist

- show that the repo was downloaded from GitHub
- show the README before running anything
- run the code from the fresh machine
- show that the code runs without errors
- explain the important files
- show the saved outputs that match the paper
