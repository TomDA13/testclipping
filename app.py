"""
YouTube Gaming Clip Detector - Flask Application
Web interface for analyzing gaming videos, downloading clips, and adding viral subtitles.
"""

import os
import re
import uuid
import subprocess
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from analyzer import analyze_video, fetch_transcript, extract_video_id
from subtitles import (
    get_available_styles,
    create_subtitle_file,
    burn_subtitles,
    get_transcript_segment,
    SUBTITLE_STYLES
)

load_dotenv()

app = Flask(__name__)

# Create directories
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Cache for transcripts
transcript_cache = {}


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

    clip_count = data.get('clip_count', 5)
    styles = data.get('styles')

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({
            'success': False,
            'error': 'ANTHROPIC_API_KEY not configured. Add it to .env file.'
        }), 500

    result = analyze_video(url, api_key, clip_count=clip_count, styles=styles)

    # Cache transcript for subtitle generation
    if result.get('success'):
        video_id = result.get('video_id')
        if video_id:
            transcript_result = fetch_transcript(video_id)
            if transcript_result.get('success'):
                transcript_cache[video_id] = transcript_result['transcript']

    return jsonify(result)


@app.route('/subtitle-styles')
def get_subtitle_styles():
    """Return available subtitle styles."""
    return jsonify({
        'success': True,
        'styles': get_available_styles()
    })


@app.route('/download', methods=['POST'])
def download_clip():
    """Download a clip from YouTube, optionally with subtitles."""
    data = request.get_json()

    required_fields = ['video_id', 'start_time', 'end_time']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    video_id = data['video_id']
    start_time = int(data['start_time'])
    end_time = int(data['end_time'])
    title = data.get('title', 'clip')
    add_subtitles = data.get('add_subtitles', False)
    subtitle_style = data.get('subtitle_style', 'tiktok')

    # Validate duration
    if end_time - start_time > 120:
        return jsonify({'success': False, 'error': 'Clip too long (max 2 minutes)'}), 400

    # Sanitize title
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
    if not safe_title:
        safe_title = 'clip'

    unique_id = uuid.uuid4().hex[:8]
    base_filename = f"{safe_title}_{start_time}-{end_time}_{unique_id}"

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # Step 1: Download video segment
        temp_video = os.path.join(TEMP_DIR, f"{base_filename}_raw.mp4")
        final_output = os.path.join(DOWNLOADS_DIR, f"{base_filename}.mp4")

        cmd = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '--download-sections', f'*{start_time}-{end_time}',
            '-o', temp_video,
            '--no-playlist',
            '--quiet',
            video_url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            # Fallback without section download
            cmd_full = [
                'yt-dlp',
                '-f', 'best[ext=mp4]/best',
                '-o', temp_video,
                '--no-playlist',
                '--quiet',
                video_url
            ]
            result = subprocess.run(cmd_full, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Download failed: {result.stderr[:200]}'
                }), 500

            # Trim with ffmpeg
            trimmed_video = os.path.join(TEMP_DIR, f"{base_filename}_trimmed.mp4")
            trim_cmd = [
                'ffmpeg', '-y',
                '-i', temp_video,
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-c', 'copy',
                trimmed_video
            ]
            subprocess.run(trim_cmd, capture_output=True, timeout=120)
            if os.path.exists(trimmed_video):
                os.replace(trimmed_video, temp_video)

        # Find the actual downloaded file (yt-dlp might modify filename)
        if not os.path.exists(temp_video):
            temp_files = [f for f in os.listdir(TEMP_DIR) if f.startswith(base_filename)]
            if temp_files:
                temp_video = os.path.join(TEMP_DIR, temp_files[0])
            else:
                return jsonify({
                    'success': False,
                    'error': 'Downloaded file not found'
                }), 500

        # Step 2: Add subtitles if requested
        if add_subtitles and subtitle_style in SUBTITLE_STYLES:
            # Get transcript segment
            transcript = transcript_cache.get(video_id)

            if not transcript:
                # Fetch transcript if not cached
                transcript_result = fetch_transcript(video_id)
                if transcript_result.get('success'):
                    transcript = transcript_result['transcript']
                    transcript_cache[video_id] = transcript

            if transcript:
                # Get segment and create subtitle file
                segment = get_transcript_segment(transcript, start_time, end_time)

                if segment:
                    sub_file = os.path.join(TEMP_DIR, f"{base_filename}.ass")
                    create_subtitle_file(segment, sub_file, subtitle_style)

                    # Burn subtitles
                    burn_result = burn_subtitles(temp_video, final_output, sub_file, subtitle_style)

                    # Cleanup subtitle file
                    if os.path.exists(sub_file):
                        os.remove(sub_file)

                    if not burn_result['success']:
                        # Fallback to video without subtitles
                        os.rename(temp_video, final_output)
                else:
                    # No transcript segment, use video as-is
                    os.rename(temp_video, final_output)
            else:
                # No transcript available
                os.rename(temp_video, final_output)
        else:
            # No subtitles requested
            os.rename(temp_video, final_output)

        # Cleanup temp files
        for f in os.listdir(TEMP_DIR):
            if f.startswith(base_filename):
                try:
                    os.remove(os.path.join(TEMP_DIR, f))
                except OSError:
                    pass

        filename = os.path.basename(final_output)

        return jsonify({
            'success': True,
            'filename': filename,
            'has_subtitles': add_subtitles
        })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Download timed out'}), 500
    except FileNotFoundError as e:
        if 'yt-dlp' in str(e):
            return jsonify({
                'success': False,
                'error': 'yt-dlp not found. Install with: pip install yt-dlp'
            }), 500
        if 'ffmpeg' in str(e):
            return jsonify({
                'success': False,
                'error': 'ffmpeg not found. Install ffmpeg for subtitle support.'
            }), 500
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download/<filename>')
def serve_download(filename):
    """Serve a downloaded clip file."""
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
