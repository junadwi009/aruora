from flask import Blueprint, jsonify, current_app

from app.services.asr import asr_ready

bp = Blueprint("health", __name__)

@bp.get("/api/health")
def health():
    cfg = current_app.config["APP_CONFIG"]
    return jsonify({
        "ok": True,
        "llmMode": cfg.LLM_MODE,
        "providerConfigured": cfg.provider_configured,
        "asrReady": asr_ready(cfg),
    })
