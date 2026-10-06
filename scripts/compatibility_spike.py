from pathlib import Path
import requests
from backend.speechlens.config import ROOT, PIPELINE
from backend.speechlens.ingest import decode
from backend.speechlens.text import canonicalize
from backend.speechlens.alignment import align
from backend.speechlens.features import extract
from backend.speechlens.utils import write_json, object_hash

TEXT = "So first of all let me assert my firm belief that the only thing we have to fear is fear itself nameless unreasoning unjustified terror which paralyzes needed efforts to convert retreat into advance. In every dark hour of our national life a leadership of frankness and vigor has met with that understanding and support of the people themselves which is essential to victory. I am convinced that you will again give that support to leadership in these critical days."

if __name__ == "__main__":
    path=ROOT/"data/originals/fdr_fear.ogg"
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        response=requests.get("https://upload.wikimedia.org/wikipedia/commons/3/35/First_Inauguration_of_FDR_-_Fear_Itself_Excerpt.ogg?download=1", timeout=90, headers={"User-Agent":"SpeechLens/0.1 research fixture"})
        response.raise_for_status()
        path.write_bytes(response.content)
    canonical=ROOT/"data/demo/fdr_reference.wav"
    canonical.parent.mkdir(parents=True,exist_ok=True)
    y,metadata=decode(path,canonical)
    text=canonicalize(TEXT)
    alignment=align(y,text,object_hash([metadata["original_sha256"],text["sha256"],PIPELINE]))
    write_json(ROOT/"data/demo/spike_alignment.json",alignment)
    print("Aligned:",alignment["coverage"],alignment["recognized_text"],flush=True)
    features=extract(y)
    write_json(ROOT/"data/demo/spike_features.json",features)
    write_json(ROOT/"data/demo/spike_transcript.json",text)
    write_json(ROOT/"evaluation/compatibility.json",{"metadata":metadata,"alignment_coverage":alignment["coverage"],
              "features":{"pitch_median_hz":features["pitch"]["median_hz"],"mfcc_shape":features["spectral"]["mfcc"].shape,
                          "quality":features["quality"]},"device":"CPU"})
    print("CPU decode/alignment/pYIN/MFCC/RMS completed.")
