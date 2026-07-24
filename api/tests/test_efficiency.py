from app.data.models import TestGate, Feedback, GenUsage


def test_models_have_expected_columns():
    assert TestGate.__tablename__ == "test_gate"
    assert set(TestGate.__table__.columns.keys()) >= {"user_id", "active_seconds", "unlocked_at"}
    assert Feedback.__tablename__ == "feedback"
    assert set(Feedback.__table__.columns.keys()) >= {"id", "user_id", "stars", "insight", "created_at"}
    assert GenUsage.__tablename__ == "gen_usage"
    assert set(GenUsage.__table__.columns.keys()) >= {"id", "user_id", "day", "count"}
