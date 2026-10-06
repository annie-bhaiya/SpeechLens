from pathlib import Path
import os
import yaml

ROOT = Path(__file__).resolve().parents[2]
STORAGE = Path(os.environ.get("SPEECHLENS_STORAGE", ROOT / "storage")).resolve()

def read_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))

PIPELINE = read_yaml("configs/pipeline.yaml")
DETECTORS = read_yaml("configs/detectors.yaml")
PRESETS = {p.stem: yaml.safe_load(p.read_text()) for p in (ROOT / "configs/rubrics").glob("*.yaml")}
