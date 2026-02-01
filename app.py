"""
YouTube Gaming Clip Detector - Flask Application
Simple web interface for analyzing gaming videos.
"""

import os
import re
import uuid
import subprocess
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from analyzer import analyze_video

load_dotenv()

app = Flask(__name__)

# Create downloads directory
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


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

    # Get optional filters
    clip_count = data.get('clip_count', 5)
    styles = data.get('styles')  # None means all styles

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({
            'success': False,
            'error': 'ANTHROPIC_API_KEY not configured. Add it to .env file.'
        }), 500

    result = analyze_video(url, api_key, clip_count=clip_count, styles=styles)
    return jsonify(result)


@app.route('/download', methods=['POST'])
def download_clip():
    """Download a clip from YouTube using yt-dlp."""
    data = request.get_json()

    required_fields = ['video_id', 'start_time', 'end_time']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    video_id = data['video_id']
    start_time = int(data['start_time'])
    end_time = int(data['end_time'])
    title = data.get('title', 'clip')

    # Sanitize title for filename
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip()
    if not safe_title:
        safe_title = 'clip'

    # Generate unique filename
    filename = f"{safe_title}_{start_time}-{end_time}_{uuid.uuid4().hex[:8]}.mp4"
    output_path = os.path.join(DOWNLOADS_DIR, filename)

    # YouTube URL
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # Use yt-dlp to download the specific segment
        # First, download with time range using yt-dlp's download_ranges
        cmd = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '--download-sections', f'*{start_time}-{end_time}',
            '--force-keyframes-at-cuts',
            '-o', output_path,
            '--no-playlist',
            video_url
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            # Try alternative method without force-keyframes
            cmd_alt = [
                'yt-dlp',
                '-f', 'best[ext=mp4]/best',
                '--download-sections', f'*{start_time}-{end_time}',
                '-o', output_path,
                '--no-playlist',
                video_url
            ]
            result = subprocess.run(
                cmd_alt,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Download failed: {result.stderr}'
                }), 500

        # Check if file was created
        if not os.path.exists(output_path):
            # yt-dlp might add format extension, try to find the file
            possible_files = [f for f in os.listdir(DOWNLOADS_DIR) if f.startswith(safe_title)]
            if possible_files:
                filename = possible_files[-1]
            else:
                return jsonify({
                    'success': False,
                    'error': 'Download completed but file not found'
                }), 500

        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'Clip downloaded successfully'
        })

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Download timed out'
        }), 500
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'yt-dlp not found. Please install it: pip install yt-dlp'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/download/<filename>')
def serve_download(filename):
    """Serve a downloaded clip file."""
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(DOWNLOADS_DIR, safe_filename)

    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': 'File not found'}), 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name=safe_filename
    )


@app.route('/clips')
def list_clips():
    """List all downloaded clips."""
    clips = []
    if os.path.exists(DOWNLOADS_DIR):
        for filename in os.listdir(DOWNLOADS_DIR):
            if filename.endswith(('.mp4', '.webm', '.mkv')):
                file_path = os.path.join(DOWNLOADS_DIR, filename)
                clips.append({
                    'filename': filename,
                    'size': os.path.getsize(file_path),
                    'created': os.path.getctime(file_path)
                })
    return jsonify({'success': True, 'clips': clips})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
