"""
YouTube Gaming Clip Detector - Flask Application
Simple web interface for analyzing gaming videos.
"""

import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from analyzer import analyze_video

load_dotenv()

app = Flask(__name__)


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze a YouTube video for clipworthy moments."""
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    url = data['url'].strip()
    if not url:
        return jsonify({'success': False, 'error': 'Empty URL'}), 400

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({
            'success': False,
            'error': 'ANTHROPIC_API_KEY not configured. Add it to .env file.'
        }), 500

    result = analyze_video(url, api_key)
    return jsonify(result)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
