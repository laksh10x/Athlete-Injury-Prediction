from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from athlete_injury_prediction.experiment import run_all_experiments

    results = run_all_experiments(repo_root)
    print(json.dumps(results["saved_files"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
