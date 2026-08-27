from app.domain.leveling import next_band, ielts_to_cefr, cefr_to_ielts, band_params, BANDS, ielts_to_cefr_approx

def test_bands_order():
    assert BANDS == ["A1A2","B1","B2","C1","C2"]

def test_next_band_caps():
    assert next_band("B1") == "B2"
    assert next_band("C2") == "C2"

def test_ielts_to_cefr():
    assert ielts_to_cefr(3.5) == "A1A2"
    assert ielts_to_cefr(4.5) == "B1"
    assert ielts_to_cefr(6.0) == "B2"
    assert ielts_to_cefr(7.5) == "C1"
    assert ielts_to_cefr(9.0) == "C2"

def test_cefr_to_ielts_b2():
    assert cefr_to_ielts("B2") == (5.5, 6.5)

def test_band_params_reading_grows_with_band():
    assert band_params("reading","B1")["length"] < band_params("reading","C1")["length"]


# ── WS02-02: CEFR approximate mapping tests ──────────────────────────────────

def test_ielts_to_cefr_approx_firm():
    """Scores well within a CEFR range return firm confidence."""
    result = ielts_to_cefr_approx(6.0)  # Well within B2 (5.5-6.5)
    assert result.level == "B2"
    assert result.confidence == "firm"
    assert result.borderline_with is None
    assert result.ielts_range == (5.5, 6.5)
    assert "PRD" in result.mapping_source


def test_ielts_to_cefr_approx_borderline_near_b2():
    """Scores near B1/B2 boundary (5.25) show B1/B2 range."""
    # 5.0 is 0.25 below 5.25 (B1→B2 boundary) → borderline B1/B2
    result = ielts_to_cefr_approx(5.0)
    assert result.confidence == "borderline"
    assert result.borderline_with == "B2"
    assert result.level == "B1/B2"
    assert result.ielts_range == (4.0, 5.0)  # B1 range


def test_ielts_to_cefr_approx_borderline_near_c1():
    """Scores near B2/C1 boundary (6.75) show B2/C1 range."""
    # 7.0 is 0.25 above 6.75 (B2→C1 boundary) → borderline B2/C1
    result = ielts_to_cefr_approx(7.0)
    assert result.confidence == "borderline"
    assert result.borderline_with == "C1"
    assert result.level == "B2/C1"
    assert result.ielts_range == (5.5, 6.5)  # B2 range


def test_ielts_to_cefr_approx_boundary_cases():
    """Test exact threshold values."""
    # 4.0 = A1A2/B1 boundary exactly → borderline A1A2/B1
    result = ielts_to_cefr_approx(4.0)
    assert result.confidence == "borderline"
    assert result.borderline_with == "B1"
    assert result.level == "A1A2/B1"
    
    # 5.25 = B1/B2 boundary exactly → borderline B1/B2
    result = ielts_to_cefr_approx(5.25)
    assert result.confidence == "borderline"
    assert result.borderline_with == "B2"
    assert result.level == "B1/B2"
    
    # 6.75 = B2/C1 boundary exactly → borderline B2/C1
    result = ielts_to_cefr_approx(6.75)
    assert result.confidence == "borderline"
    assert result.borderline_with == "C1"
    assert result.level == "B2/C1"
    
    # 8.25 = C1/C2 boundary exactly → borderline C1/C2
    result = ielts_to_cefr_approx(8.25)
    assert result.confidence == "borderline"
    assert result.borderline_with == "C2"
    assert result.level == "C1/C2"
