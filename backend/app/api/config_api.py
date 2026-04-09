"""
API Configuration Endpoints - Provider Switching
"""

from flask import jsonify, request

from . import config_bp
from ..config import Config


@config_bp.route('/provider', methods=['GET'])
def get_provider():
    """Get current LLM provider"""
    if Config.LLM_PROVIDER == 'anthropic':
        model = Config.ANTHROPIC_MODEL
    else:
        model = Config.LLM_MODEL_NAME
    return jsonify({
        "provider": Config.LLM_PROVIDER,
        "model": model
    })


@config_bp.route('/provider', methods=['POST'])
def set_provider():
    """Switch LLM provider (at runtime)"""
    data = request.get_json()
    provider = data.get('provider')
    if provider not in ('lm-studio', 'anthropic'):
        return jsonify({
            "error": "Il provider deve essere 'lm-studio' o 'anthropic'"
        }), 400

    Config.LLM_PROVIDER = provider
    return jsonify({"success": True, "provider": provider})
