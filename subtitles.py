"""
Viral Subtitle Generator
Creates styled subtitles for video clips in various viral formats.
"""

import os
import subprocess


# Subtitle style presets - MUCH BIGGER sizes for viral effect
SUBTITLE_STYLES = {
    "tiktok": {
        "name": "TikTok Viral",
        "description": "Bold, centered, white with black outline",
        "fontname": "Arial Black",
        "fontsize": 72,  # Much bigger
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "bold": 1,
        "outline": 5,
        "shadow": 2,
        "alignment": 2,
        "margin_v": 80,
        "preview_css": "font-family: 'Arial Black', sans-serif; font-size: 32px; color: white; text-shadow: -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000; font-weight: bold; text-transform: uppercase;"
    },
    "youtube_shorts": {
        "name": "YouTube Shorts",
        "description": "Yellow text, bold, gaming style",
        "fontname": "Impact",
        "fontsize": 78,
        "primary_color": "&H0000FFFF",  # Yellow (BGR)
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "bold": 1,
        "outline": 6,
        "shadow": 3,
        "alignment": 2,
        "margin_v": 70,
        "preview_css": "font-family: Impact, sans-serif; font-size: 34px; color: #FFFF00; text-shadow: -5px -5px 0 #000, 5px -5px 0 #000, -5px 5px 0 #000, 5px 5px 0 #000; font-weight: bold; text-transform: uppercase;"
    },
    "mrbeast": {
        "name": "MrBeast Style",
        "description": "Big, bold, white with red accent",
        "fontname": "Arial Black",
        "fontsize": 80,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H000000FF",  # Red (BGR)
        "back_color": "&H00000000",
        "bold": 1,
        "outline": 6,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 90,
        "preview_css": "font-family: 'Arial Black', sans-serif; font-size: 36px; color: white; text-shadow: -5px -5px 0 #FF0000, 5px -5px 0 #FF0000, -5px 5px 0 #FF0000, 5px 5px 0 #FF0000; font-weight: bold; text-transform: uppercase;"
    },
    "minimal": {
        "name": "Minimal Clean",
        "description": "Simple white text, subtle shadow",
        "fontname": "Helvetica Neue",
        "fontsize": 64,
        "primary_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "back_color": "&H40000000",
        "bold": 1,
        "outline": 3,
        "shadow": 2,
        "alignment": 2,
        "margin_v": 60,
        "preview_css": "font-family: Helvetica, Arial, sans-serif; font-size: 28px; color: white; text-shadow: 3px 3px 6px rgba(0,0,0,0.9); font-weight: bold;"
    },
    "neon": {
        "name": "Neon Glow",
        "description": "Cyan neon glow effect",
        "fontname": "Arial Black",
        "fontsize": 70,
        "primary_color": "&H00FFFF00",  # Cyan (BGR)
        "outline_color": "&H00FF8000",  # Blue glow
        "back_color": "&H00000000",
        "bold": 1,
        "outline": 5,
        "shadow": 4,
        "alignment": 2,
        "margin_v": 75,
        "preview_css": "font-family: 'Arial Black', sans-serif; font-size: 32px; color: #00FFFF; text-shadow: 0 0 15px #00FFFF, 0 0 30px #00FFFF, 0 0 45px #0080FF; font-weight: bold;"
    },
    "karaoke": {
        "name": "Karaoke Green",
        "description": "Bright green highlight style",
        "fontname": "Arial Black",
        "fontsize": 74,
        "primary_color": "&H0000FF00",  # Green (BGR)
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "bold": 1,
        "outline": 5,
        "shadow": 2,
        "alignment": 2,
        "margin_v": 80,
        "preview_css": "font-family: 'Arial Black', sans-serif; font-size: 32px; color: #00FF00; text-shadow: -4px -4px 0 #000, 4px -4px 0 #000, -4px 4px 0 #000, 4px 4px 0 #000; font-weight: bold; text-transform: uppercase;"
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
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['fontname']},{style['fontsize']},{style['primary_color']},{style.get('secondary_color', style['primary_color'])},{style['outline_color']},{style['back_color']},{style['bold']},0,0,0,100,100,1,0,1,{style['outline']},{style['shadow']},{style['alignment']},20,20,{style['margin_v']},1

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


def transcript_to_ass(transcript: list, style_key: str = "tiktok", words_per_line: int = 4) -> str:
    """
    Convert transcript to ASS subtitle format.
    Shorter lines = bigger text feel, more viral style.
    """
    ass_content = generate_ass_style(style_key)
    style = SUBTITLE_STYLES.get(style_key, SUBTITLE_STYLES["tiktok"])

    for entry in transcript:
        start_time = format_ass_time(entry['start'])
        end_time = format_ass_time(entry['start'] + entry.get('duration', 2.5))
        text = entry['text'].strip().replace('\n', ' ')

        # Clean up text
        text = text.replace('  ', ' ')

        # Split into shorter chunks for viral style
        words = text.split()
        if len(words) > words_per_line:
            # Split into multiple lines within same subtitle
            lines = []
            for i in range(0, len(words), words_per_line):
                lines.append(' '.join(words[i:i+words_per_line]))
            text = '\\N'.join(lines[:2])  # Max 2 lines

        # Uppercase for more impact on certain styles
        if style_key in ['mrbeast', 'youtube_shorts', 'tiktok', 'karaoke']:
            text = text.upper()

        ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"

    return ass_content


def create_subtitle_file(transcript: list, output_path: str, style_key: str = "tiktok") -> bool:
    """Create an ASS subtitle file from transcript."""
    try:
        ass_content = transcript_to_ass(transcript, style_key)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        return True
    except Exception as e:
        print(f"Error creating subtitle file: {e}")
        return False


def burn_subtitles(input_video: str, output_video: str, subtitle_file: str, style_key: str = "tiktok") -> dict:
    """Burn subtitles into video using ffmpeg."""
    try:
        # Use fontsdir if available, escape path properly
        sub_path = subtitle_file.replace('\\', '/').replace(':', '\\:').replace("'", "\\'")

        cmd = [
            'ffmpeg',
            '-y',
            '-i', input_video,
            '-vf', f"subtitles='{sub_path}'",
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            output_video
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            # Try alternative filter syntax
            cmd_alt = [
                'ffmpeg',
                '-y',
                '-i', input_video,
                '-vf', f"ass={sub_path}",
                '-c:a', 'copy',
                '-c:v', 'libx264',
                '-preset', 'fast',
                output_video
            ]
            result = subprocess.run(cmd_alt, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                return {'success': False, 'error': f'FFmpeg error: {result.stderr[:300]}'}

        return {'success': True}

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Subtitle burning timed out'}
    except FileNotFoundError:
        return {'success': False, 'error': 'ffmpeg not found. Install ffmpeg.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_transcript_segment(full_transcript: list, start_time: int, end_time: int) -> list:
    """Extract transcript segment between start and end times."""
    segment = []
    for entry in full_transcript:
        entry_start = entry['start']
        entry_end = entry_start + entry.get('duration', 2)

        if entry_end > start_time and entry_start < end_time:
            adjusted_entry = {
                'start': max(0, entry_start - start_time),
                'duration': entry.get('duration', 2),
                'text': entry['text']
            }
            segment.append(adjusted_entry)

    return segment
