"""
Viral Subtitle Generator
Creates styled subtitles for video clips in various viral formats.
"""

import os
import subprocess
import json
from typing import Optional


# Subtitle style presets
SUBTITLE_STYLES = {
    "tiktok": {
        "name": "TikTok Viral",
        "description": "Bold, centered, white with black outline",
        "fontname": "Arial Black",
        "fontsize": 24,
        "primary_color": "&H00FFFFFF",  # White
        "outline_color": "&H00000000",  # Black
        "back_color": "&H80000000",     # Semi-transparent black
        "bold": 1,
        "outline": 3,
        "shadow": 1,
        "alignment": 2,  # Bottom center
        "margin_v": 60,
        "preview_css": "font-family: 'Arial Black', sans-serif; font-size: 28px; color: white; text-shadow: -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000; text-align: center; font-weight: bold;"
    },
    "youtube_shorts": {
        "name": "YouTube Shorts",
        "description": "Yellow text, bold, gaming style",
        "fontname": "Impact",
        "fontsize": 26,
        "primary_color": "&H0000FFFF",  # Yellow
        "outline_color": "&H00000000",  # Black
        "back_color": "&H00000000",
        "bold": 1,
        "outline": 4,
        "shadow": 2,
        "alignment": 2,
        "margin_v": 50,
        "preview_css": "font-family: Impact, sans-serif; font-size: 30px; color: #FFFF00; text-shadow: -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000; text-align: center; font-weight: bold;"
    },
    "mrbeast": {
        "name": "MrBeast Style",
        "description": "Big, bold, white with red accent",
        "fontname": "Arial Black",
        "fontsize": 28,
        "primary_color": "&H00FFFFFF",  # White
        "outline_color": "&H000000FF",  # Red
        "back_color": "&H00000000",
        "bold": 1,
        "outline": 4,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 70,
        "preview_css": "font-family: 'Arial Black', sans-serif; font-size: 32px; color: white; text-shadow: -4px -4px 0 #FF0000, 4px -4px 0 #FF0000, -4px 4px 0 #FF0000, 4px 4px 0 #FF0000; text-align: center; font-weight: bold; text-transform: uppercase;"
    },
    "minimal": {
        "name": "Minimal Clean",
        "description": "Simple white text, subtle shadow",
        "fontname": "Helvetica",
        "fontsize": 22,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H40000000",
        "bold": 0,
        "outline": 2,
        "shadow": 1,
        "alignment": 2,
        "margin_v": 40,
        "preview_css": "font-family: Helvetica, Arial, sans-serif; font-size: 24px; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); text-align: center;"
    },
    "neon": {
        "name": "Neon Glow",
        "description": "Cyan neon glow effect",
        "fontname": "Arial Black",
        "fontsize": 24,
        "primary_color": "&H00FFFF00",  # Cyan
        "outline_color": "&H00FF0000",  # Blue glow
        "back_color": "&H00000000",
        "bold": 1,
        "outline": 3,
        "shadow": 3,
        "alignment": 2,
        "margin_v": 50,
        "preview_css": "font-family: 'Arial Black', sans-serif; font-size: 28px; color: #00FFFF; text-shadow: 0 0 10px #00FFFF, 0 0 20px #00FFFF, 0 0 30px #0080FF; text-align: center; font-weight: bold;"
    },
    "karaoke": {
        "name": "Karaoke Word-by-Word",
        "description": "Highlights each word as spoken",
        "fontname": "Arial Black",
        "fontsize": 26,
        "primary_color": "&H0000FF00",  # Green (highlighted)
        "secondary_color": "&H00FFFFFF",  # White (not yet spoken)
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "bold": 1,
        "outline": 3,
        "shadow": 1,
        "alignment": 2,
        "margin_v": 55,
        "preview_css": "font-family: 'Arial Black', sans-serif; font-size: 28px; color: #00FF00; text-shadow: -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000; text-align: center; font-weight: bold;"
    }
}


def get_available_styles() -> dict:
    """Return all available subtitle styles with their metadata."""
    return {
        key: {
            "name": style["name"],
            "description": style["description"],
            "preview_css": style["preview_css"]
        }
        for key, style in SUBTITLE_STYLES.items()
    }


def generate_ass_style(style_key: str) -> str:
    """Generate ASS subtitle style definition."""
    style = SUBTITLE_STYLES.get(style_key, SUBTITLE_STYLES["tiktok"])

    return f"""[Script Info]
Title: Viral Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['fontname']},{style['fontsize']},{style['primary_color']},{style.get('secondary_color', style['primary_color'])},{style['outline_color']},{style['back_color']},{style['bold']},0,0,0,100,100,0,0,1,{style['outline']},{style['shadow']},{style['alignment']},10,10,{style['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format (H:MM:SS.CC)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def transcript_to_ass(transcript: list, style_key: str = "tiktok", words_per_line: int = 5) -> str:
    """
    Convert transcript to ASS subtitle format.

    Args:
        transcript: List of {'start': float, 'duration': float, 'text': str}
        style_key: Subtitle style to use
        words_per_line: Max words per subtitle line
    """
    ass_content = generate_ass_style(style_key)

    for entry in transcript:
        start_time = format_ass_time(entry['start'])
        end_time = format_ass_time(entry['start'] + entry.get('duration', 2))
        text = entry['text'].strip().replace('\n', ' ')

        # Split long text into multiple lines
        words = text.split()
        if len(words) > words_per_line:
            mid = len(words) // 2
            text = ' '.join(words[:mid]) + '\\N' + ' '.join(words[mid:])

        # Convert to uppercase for more impact (optional based on style)
        if style_key in ['mrbeast', 'youtube_shorts']:
            text = text.upper()

        ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"

    return ass_content


def create_subtitle_file(transcript: list, output_path: str, style_key: str = "tiktok") -> bool:
    """
    Create an ASS subtitle file from transcript.

    Returns True if successful.
    """
    try:
        ass_content = transcript_to_ass(transcript, style_key)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        return True
    except Exception as e:
        print(f"Error creating subtitle file: {e}")
        return False


def burn_subtitles(
    input_video: str,
    output_video: str,
    subtitle_file: str,
    style_key: str = "tiktok"
) -> dict:
    """
    Burn subtitles into video using ffmpeg.

    Returns dict with success status and error message if failed.
    """
    try:
        # Escape the subtitle file path for ffmpeg filter
        escaped_sub_path = subtitle_file.replace('\\', '/').replace(':', '\\:')

        cmd = [
            'ffmpeg',
            '-i', input_video,
            '-vf', f"ass={escaped_sub_path}",
            '-c:a', 'copy',
            '-y',  # Overwrite output
            output_video
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode != 0:
            return {
                'success': False,
                'error': f'FFmpeg error: {result.stderr}'
            }

        return {'success': True}

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Subtitle burning timed out'}
    except FileNotFoundError:
        return {'success': False, 'error': 'ffmpeg not found. Please install ffmpeg.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_transcript_segment(full_transcript: list, start_time: int, end_time: int) -> list:
    """
    Extract transcript segment between start and end times.
    Adjusts timestamps to be relative to clip start.
    """
    segment = []
    for entry in full_transcript:
        entry_start = entry['start']
        entry_end = entry_start + entry.get('duration', 2)

        # Check if entry overlaps with our segment
        if entry_end > start_time and entry_start < end_time:
            # Adjust timestamp relative to clip start
            adjusted_entry = {
                'start': max(0, entry_start - start_time),
                'duration': entry.get('duration', 2),
                'text': entry['text']
            }
            segment.append(adjusted_entry)

    return segment
