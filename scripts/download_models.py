from backend.speechlens.alignment import load_model
from backend.speechlens.config import PIPELINE
from backend.speechlens.utils import write_json, sha256_file
from backend.speechlens.config import ROOT

if __name__ == "__main__":
    load_model()
    files = list((ROOT / ".cache/models").rglob("*.safetensors"))
    write_json(ROOT / "releases/model_manifest.json", {"model": PIPELINE["alignment_model"],
        "revision": PIPELINE["alignment_revision"], "license": "Apache-2.0",
        "files": [{"name": p.name, "sha256": sha256_file(p)} for p in files]})
    print("Pinned CPU alignment model ready.")
