from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
import json

app = Flask(__name__)
CORS(app)

# Data paths
DATA_DIR = 'data_analysis'
FINAL_DATA_PATH = os.path.join(DATA_DIR, 'qidian_final_model.csv')
VISUALIZE_DATA_PATH = os.path.join('data_analysis_v3', 'final_featured_data.csv')

@app.route('/api/novels', methods=['GET'])
def get_novels():
    """Get novels with pagination and filtering"""
    try:
        if not os.path.exists(FINAL_DATA_PATH):
            return jsonify({'error': 'Data not found'}), 404
            
        df = pd.read_csv(FINAL_DATA_PATH)
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        start = (page - 1) * per_page
        end = start + per_page
        
        # Filtering
        category = request.args.get('category')
        if category:
            df = df[df['category'].str.contains(category, case=False, na=False)]
            
        min_score = request.args.get('min_score')
        if min_score:
            df = df[df['IP_Value'] >= float(min_score)]
        
        # Sorting
        sort_by = request.args.get('sort', 'IP_Value')
        sort_order = request.args.get('order', 'desc')
        ascending = sort_order == 'asc'
        df = df.sort_values(sort_by, ascending=ascending)
        
        total = len(df)
        novels = df.iloc[start:end].to_dict('records')
        
        return jsonify({
            'novels': novels,
            'total': total,
            'page': page,
            'per_page': per_page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/novels/<int:novel_id>', methods=['GET'])
def get_novel_detail(novel_id):
    """Get detailed information for a specific novel"""
    try:
        if not os.path.exists(FINAL_DATA_PATH):
            return jsonify({'error': 'Data not found'}), 404
            
        df = pd.read_csv(FINAL_DATA_PATH)
        
        # For now, use index as ID (in real app, use proper ID)
        if novel_id >= len(df):
            return jsonify({'error': 'Novel not found'}), 404
            
        novel = df.iloc[novel_id].to_dict()
        
        return jsonify(novel)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    try:
        if not os.path.exists(FINAL_DATA_PATH):
            return jsonify({'error': 'Data not found'}), 404
            
        df = pd.read_csv(FINAL_DATA_PATH)
        
        stats = {
            'total_novels': len(df),
            'avg_ip_value': round(df['IP_Value'].mean(), 2),
            'top_categories': df['category'].value_counts().head(5).to_dict(),
            'grade_distribution': df['Grade'].value_counts().to_dict()
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/visualization-data', methods=['GET'])
def get_visualization_data():
    """Get data for visualizations"""
    try:
        data = {}
        
        if os.path.exists(FINAL_DATA_PATH):
            df = pd.read_csv(FINAL_DATA_PATH)
            
            # Top 10 IP values
            top10 = df.nlargest(10, 'IP_Value')[['title', 'IP_Value']].to_dict('records')
            data['top10_ip'] = top10
            
            # Grade distribution
            data['grade_dist'] = df['Grade'].value_counts().to_dict()
            
            # Category distribution
            data['category_dist'] = df['category'].value_counts().head(10).to_dict()
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)