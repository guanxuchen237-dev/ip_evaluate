from flask import Flask
from flask_cors import CORS
from api import api_bp

app = Flask(__name__)
# Enable CORS for all routes, specifically allowing localhost:5173 (Vite default)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register Blueprints
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def index():
    return "Novel Visualization API is running. Access endpoints at /api/*"

if __name__ == '__main__':
    print("🚀 Starting Flask Server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
