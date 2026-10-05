"""Run inside the final API image with Docker --network=none."""
import importlib.metadata
import importlib.util
import json
import sys
sys.path.insert(0, "/app")
from app.services.essay_metrics import compute_metrics
from app.services.metric_resources import PROFILE, load_resources
from faster_whisper import WhisperModel

for name in ("nltk", "textstat", "lexicalrichness", "textblob"):
    assert importlib.util.find_spec(name) is None, f"Unexpected runtime dependency: {name}"
metrics = compute_metrics("Independent learners benefit from clear feedback and reliable practice. " * 6)
assert metrics["syntax"] is not None
assert metrics["readability"]["fleschKincaidGrade"] != 0
assert metrics["lexicalDiversity"]["mtld"] is not None
model = WhisperModel("base", device="cpu", compute_type="int8", local_files_only=True)
counts, easy = load_resources()
print(json.dumps({"metricProfile": PROFILE, "dictionaryWords": len(counts),
    "easyWords": len(easy), "metricsWithoutNetwork": True, "spacySyntaxAvailable": True,
    "whisperBaseLoadedWithoutNetwork": True, "nltkDistributionAbsent": True,
    "versions": {p: importlib.metadata.version(p) for p in
                 ("pyphen", "spacy", "textdescriptives", "en-core-web-sm", "faster-whisper")}}, sort_keys=True))
