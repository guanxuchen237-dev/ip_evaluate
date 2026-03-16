from flask import Blueprint, request, jsonify
from flask_cors import CORS
import pandas as pd
import joblib
import os
# from snownlp import SnowNLP # Disabled for stability
import jieba
from gensim import corpora, models
import numpy as np

# Absolute imports for app.py execution context
try:
    from data_manager import data_manager
    from ai_service import ai_service
except ImportError:
    from backend.data_manager import data_manager
    from backend.ai_service import ai_service


api_bp = Blueprint('api', __name__)

# --- 1. Dashboard Charts API ---

@api_bp.route('/stats/overview')
def stats_overview():
    stats = data_manager.get_overview_stats()
    return jsonify(stats)

@api_bp.route('/charts/rank')
def chart_rank():
    data = data_manager.get_top_ip_novels(limit=10)
    return jsonify(data)

@api_bp.route('/charts/distribution')
def chart_distribution():
    data = data_manager.get_category_distribution()
    return jsonify(data)

@api_bp.route('/charts/trend')
def chart_trend():
    data = data_manager.get_interaction_trend()
    return jsonify(data)

@api_bp.route('/charts/platform')
def chart_platform():
    data = data_manager.get_platform_distribution()
    return jsonify(data)

@api_bp.route('/charts/wordcloud')
def chart_wordcloud():
    data = data_manager.get_wordcloud_data()
    return jsonify(data)

@api_bp.route('/charts/radar')
def chart_radar():
    data = data_manager.get_radar_data()
    return jsonify(data)

@api_bp.route('/charts/scatter')
def chart_scatter():
    data = data_manager.get_scatter_data()
    return jsonify(data)

@api_bp.route('/charts/correlation')
def chart_correlation():
    data = data_manager.get_correlation_matrix()
    return jsonify(data)

@api_bp.route('/charts/author_tiers')
def chart_author_tiers():
    data = data_manager.get_author_tiers()
    return jsonify(data)

# --- 2. Prediction API ---
# Trigger Reload for Category Calibration
@api_bp.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        title = data.get('title', '')
        abstract = data.get('abstract', '')
        category = data.get('category', '都市')
        
        # DEBUG LOG
        with open("backend_debug.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[API] Predict Called for: {title}\n")
            f.write(f"[API] Model Loaded? {data_manager.model is not None}\n")
            
        print(f"🔮 Predicting for: {title}")
        
        # 1. Prediction (V2)
        if data_manager.model:
            try:
                prediction_result = data_manager.predict_ip(data)
                result = prediction_result
                
                # Extract metrics for AI analysis
                details = result.get('details', {})
                velocity = details.get('velocity_score', 0)
                trend = details.get('trend_score', 0.5)
                intensity = details.get('sentiment_intensity', 0)
                
            except Exception as e:
                with open("backend_debug.txt", "a", encoding="utf-8") as f:
                     f.write(f"[API] DataManager Predict Error: {e}\n")
                print(f"❌ Prediction Error: {e}")
                import traceback; traceback.print_exc()
                result = {'score': 60.0, 'error': str(e), 'details': {}}
                velocity=0; trend=0.5; intensity=0
        else:
            with open("backend_debug.txt", "a", encoding="utf-8") as f:
                 f.write(f"[API] Model Missing. Returning default.\n")
            result = {'score': 60.0, 'model_version': 'v1', 'details': {}}
            velocity=0; trend=0.5; intensity=0
            
    except Exception as outer_e:
        with open("backend_debug.txt", "a", encoding="utf-8") as f:
             f.write(f"[API] CRITICAL FAILURE: {outer_e}\n")
        return jsonify({'error': str(outer_e)}), 500

    # 3. AI Analysis (Fail-Safe)
    try:
        ai_report = ai_service.analyze_prediction(
            title, category, result['score'], abstract,
            velocity=velocity, trend=trend, intensity=intensity
        )
        result['ai_report'] = ai_report
    except Exception as e:
        print(f"⚠️ AI Failed: {e}")
        result['ai_report'] = ai_service._mock_response()

    return jsonify(result)

@api_bp.route('/config/categories')
def config_categories():
    cats = list(data_manager.category_stats.keys()) if data_manager.category_stats else ['玄幻', '都市']
    return jsonify({'categories': cats})
