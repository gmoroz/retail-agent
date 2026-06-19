"""Filesystem paths used by the eval harness."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = PROJECT_ROOT / "eval"
DEFAULT_SEED_PATH = EVAL_DIR / "seed_trios.json"
DEFAULT_GOLDEN_SET_PATH = EVAL_DIR / "golden_set.json"
DEFAULT_RESULTS_JSON_PATH = EVAL_DIR / "results.json"
DEFAULT_RESULTS_MD_PATH = EVAL_DIR / "results.md"
