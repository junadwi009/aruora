import json
import pytest
from app.config import Config
from app.services.llm import LlmGateway
from app.errors import ApiError

class _FakeMsg:  # minimal OpenAI response shims
    def __init__(self, content): self.message = type("M", (), {"content": content})
class _FakeResp:
    def __init__(self, content): self.choices = [_FakeMsg(content)]
class _FakeChat:
    def __init__(self, recorder): self._rec = recorder
    def create(self, model, messages, **kw):
        self._rec["model"] = model
        self._rec["messages"] = messages
        return _FakeResp(self._rec["reply"])
class _FakeClient:
    def __init__(self, recorder): self.chat = type("C", (), {"completions": _FakeChat(recorder)})

_VALID_WRITING = ('{"bands":{"taskResponse":6.0,"coherenceCohesion":6.0,'
                  '"lexicalResource":6.0,"grammaticalRange":6.0,"overall":6.0},'
                  '"cefr":"B2","corrections":[],"rewrite":"r","modelAnswer":"m"}')
_VALID_READING = ('{"title":"t","passage":"p","questions":[{"type":"tfng",'
                  '"stem":"s","options":["True","False","Not Given"],'
                  '"answer":"True","explanation":"e"}]}')

def _gw(reply):
    gw = LlmGateway(Config({"LLM_MODE": "live", "OPENROUTER_API_KEY": "x",
                            "MODEL_GENERATE": "gen-model", "MODEL_SCORE": "score-model"}))
    rec = {"reply": reply}
    gw._openai_client = _FakeClient(rec)   # inject the fake; bypass real OpenAI()
    gw._rec = rec
    return gw, rec

def test_generate_routes_to_model_generate():
    gw, rec = _gw(_VALID_READING)
    out = gw.generate("generate", skill="reading", band="B2")
    assert rec["model"] == "gen-model"        # cheap model for generation (SC-006)
    assert out["passage"] == "p"
    assert "stub" not in out                   # live path does not set stub

def test_score_routes_to_model_score():
    gw, rec = _gw(_VALID_WRITING)
    out = gw.score("writing", taskType="task2", prompt="p", essay="hello",
                   metricsSummary="words=1")
    assert rec["model"] == "score-model"       # strong model for scoring (SC-006)
    assert out["bands"]["overall"] == 6.0

def test_live_strips_code_fences():
    fenced = '```json\n{"bands":{"taskResponse":5.5,"coherenceCohesion":5.5,' \
             '"lexicalResource":5.0,"grammaticalRange":5.0,"overall":5.5},' \
             '"cefr":"B1","corrections":[],"rewrite":"r","modelAnswer":"m"}\n```'
    gw, rec = _gw(fenced)
    out = gw.score("writing", taskType="task2", prompt="p", essay="x",
                   metricsSummary="")
    assert out["cefr"] == "B1"

def test_live_no_key_raises():
    gw = LlmGateway(Config({"LLM_MODE": "live"}))  # no OPENROUTER_API_KEY
    with pytest.raises(ApiError):
        gw.generate("generate", skill="reading", band="B2")

def test_live_never_returns_key():
    sneaky = ('{"bands":{"taskResponse":6.0,"coherenceCohesion":6.0,'
              '"lexicalResource":6.0,"grammaticalRange":6.0,"overall":6.0},'
              '"cefr":"B2","corrections":[],"rewrite":"r","modelAnswer":"m",'
              '"api_key":"LEAK"}')
    gw, rec = _gw(sneaky)
    out = gw.score("writing", taskType="task2", prompt="p", essay="x",
                   metricsSummary="")
    blob = json.dumps(out)
    assert "api_key" not in blob and "OPENROUTER_API_KEY" not in blob


def test_score_attaches_metadata_envelope():
    """WS02-03/05-08: live scoring carries the transparency + audit envelopes."""
    gw, rec = _gw(_VALID_WRITING)
    out = gw.score("writing", taskType="task2", prompt="p", essay="x",
                   metricsSummary="")
    meta = out["score_metadata"]
    assert meta["score_method"] == "llm_estimate"
    assert meta["model_provider"] == "openrouter"
    assert meta["model_id"] == "score-model"   # actual requested model, not an alias
    for k in ("prompt_version", "rubric_version", "calibration_version", "score_version"):
        assert k in meta
    audit = out["_meta_llm"]
    assert audit["requestedModel"] == "score-model"
    assert isinstance(audit["latencyMs"], int)


def test_stub_score_attaches_metadata_envelope():
    """WS02-03/05-08: stub scoring also carries both envelopes."""
    from app.config import Config
    gw = LlmGateway(Config({"LLM_MODE": "stub"}))
    out = gw.score("writing")
    assert out["stub"] is True
    assert out["score_metadata"]["model_id"] == "stub"
    assert out["_meta_llm"]["provider"] == "stub"


def test_invalid_live_output_is_controlled_llm_bad_output():
    gw, rec = _gw('{"bands":{"overall":999}}')     # fails its schema
    with pytest.raises(ApiError) as ei:
        gw.score("writing", taskType="task2", prompt="p", essay="x",
                 metricsSummary="")
    assert ei.value.code == "LLM_BAD_OUTPUT"