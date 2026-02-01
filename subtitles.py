"""
Viral Subtitle Generator - Word-by-Word Karaoke Style
Creates TikTok/Shorts style subtitles with word highlighting and animations.
"""

import os
import re
import subprocess
from typing import List, Dict


# Configuration
CONFIG = {
    'max_words_per_chunk': 5,
    'min_words_per_chunk': 2,
    'max_chars_per_line': 18,
    'max_lines': 2,
    'min_chunk_duration_ms': 450,
    'hold_ms': 150,  # Hold after last word
    'silence_threshold_ms': 220,  # Split on silence > this
    'fade_in_ms': 80,
    'fade_out_ms': 60,
}


# Style presets optimized for viral look
SUBTITLE_STYLES = {
    "tiktok": {
        "name": "TikTok Viral",
        "fontname": "Arial Black",
        "fontsize": 68,
        "primary_color": "&H00FFFFFF",  # White
        "highlight_color": "&H0000D4FF",  # Cyan highlight
        "outline_color": "&H00000000",
        "shadow_color": "&H80000000",
        "outline": 8,
        "shadow": 4,
        "bold": 1,
        "spacing": 0,
    },
    "youtube_shorts": {
        "name": "YouTube Shorts",
        "fontname": "Impact",
        "fontsize": 72,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000FFFF",  # Yellow
        "outline_color": "&H00000000",
        "shadow_color": "&H80000000",
        "outline": 10,
        "shadow": 5,
        "bold": 1,
        "spacing": 1,
    },
    "mrbeast": {
        "name": "MrBeast Style",
        "fontname": "Arial Black",
        "fontsize": 76,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H000000FF",  # Red
        "outline_color": "&H000000FF",  # Red outline
        "shadow_color": "&H40000000",
        "outline": 8,
        "shadow": 3,
        "bold": 1,
        "spacing": 0,
    },
    "minimal": {
        "name": "Minimal Clean",
        "fontname": "Helvetica Neue",
        "fontsize": 60,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000D4FF",
        "outline_color": "&H00000000",
        "shadow_color": "&H60000000",
        "outline": 5,
        "shadow": 6,
        "bold": 1,
        "spacing": 0,
    },
    "neon": {
        "name": "Neon Glow",
        "fontname": "Arial Black",
        "fontsize": 66,
        "primary_color": "&H00FFFF00",  # Cyan
        "highlight_color": "&H00FF00FF",  # Magenta
        "outline_color": "&H00FF8000",
        "shadow_color": "&H00FF8000",
        "outline": 6,
        "shadow": 8,
        "bold": 1,
        "spacing": 1,
    },
    "karaoke": {
        "name": "Karaoke Green",
        "fontname": "Arial Black",
        "fontsize": 70,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000FF00",  # Green
        "outline_color": "&H00000000",
        "shadow_color": "&H80000000",
        "outline": 7,
        "shadow": 4,
        "bold": 1,
        "spacing": 0,
    }
}


def estimate_word_timestamps(segment: Dict) -> List[Dict]:
    """
    Estimate word-level timestamps from a transcript segment.
    Distributes time proportionally based on word length.
    """
    text = segment['text'].strip()
    if not text:
        return []

    words = text.split()
    if not words:
        return []

    start_ms = int(segment['start'] * 1000)
    duration_ms = int(segment.get('duration', 2) * 1000)
    end_ms = start_ms + duration_ms

    # Calculate total character count (for proportional timing)
    total_chars = sum(len(w) for w in words)
    if total_chars == 0:
        total_chars = len(words)

    word_timestamps = []
    current_ms = start_ms

    for word in words:
        # Proportional duration based on word length
        word_duration = int((len(word) / total_chars) * duration_ms)
        word_duration = max(word_duration, 80)  # Minimum 80ms per word

        word_timestamps.append({
            'word': word,
            'start_ms': current_ms,
            'end_ms': min(current_ms + word_duration, end_ms),
        })
        current_ms += word_duration

    # Adjust last word to end at segment end
    if word_timestamps:
        word_timestamps[-1]['end_ms'] = end_ms

    return word_timestamps


def create_chunks(word_timestamps: List[Dict]) -> List[Dict]:
    """
    Group words into display chunks (2-5 words each).
    Respects silence thresholds and punctuation.
    """
    if not word_timestamps:
        return []

    chunks = []
    current_chunk_words = []
    current_chunk_start = None

    for i, wt in enumerate(word_timestamps):
        word = wt['word']

        if current_chunk_start is None:
            current_chunk_start = wt['start_ms']

        current_chunk_words.append(wt)

        # Check if we should end the chunk
        should_end = False

        # Max words reached
        if len(current_chunk_words) >= CONFIG['max_words_per_chunk']:
            should_end = True

        # Punctuation (end of sentence)
        if word.rstrip()[-1:] in '.!?':
            should_end = True

        # Check for silence before next word
        if i < len(word_timestamps) - 1:
            next_start = word_timestamps[i + 1]['start_ms']
            gap = next_start - wt['end_ms']
            if gap > CONFIG['silence_threshold_ms']:
                should_end = True

        # Last word
        if i == len(word_timestamps) - 1:
            should_end = True

        if should_end and len(current_chunk_words) >= CONFIG['min_words_per_chunk']:
            chunk_end = wt['end_ms'] + CONFIG['hold_ms']

            # Ensure minimum duration
            chunk_duration = chunk_end - current_chunk_start
            if chunk_duration < CONFIG['min_chunk_duration_ms']:
                chunk_end = current_chunk_start + CONFIG['min_chunk_duration_ms']

            chunks.append({
                'words': current_chunk_words.copy(),
                'start_ms': current_chunk_start,
                'end_ms': chunk_end,
                'text': ' '.join(w['word'] for w in current_chunk_words)
            })

            current_chunk_words = []
            current_chunk_start = None

        elif should_end and current_chunk_words:
            # Not enough words but need to end - keep accumulating
            # unless it's the last word
            if i == len(word_timestamps) - 1:
                chunk_end = wt['end_ms'] + CONFIG['hold_ms']
                chunks.append({
                    'words': current_chunk_words.copy(),
                    'start_ms': current_chunk_start,
                    'end_ms': chunk_end,
                    'text': ' '.join(w['word'] for w in current_chunk_words)
                })

    return chunks


def format_ass_time(ms: int) -> str:
    """Convert milliseconds to ASS timestamp format (H:MM:SS.CC)."""
    total_seconds = ms / 1000
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    centiseconds = int((total_seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def generate_ass_header(style_key: str) -> str:
    """Generate ASS file header with styles."""
    style = SUBTITLE_STYLES.get(style_key, SUBTITLE_STYLES["tiktok"])

    return f"""[Script Info]
Title: Viral Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['fontname']},{style['fontsize']},{style['primary_color']},{style['highlight_color']},{style['outline_color']},{style['shadow_color']},{style['bold']},0,0,0,100,100,{style['spacing']},0,1,{style['outline']},{style['shadow']},2,40,40,80,1
Style: Highlight,{style['fontname']},{style['fontsize']},{style['highlight_color']},{style['primary_color']},{style['outline_color']},{style['shadow_color']},{style['bold']},0,0,0,100,100,{style['spacing']},0,1,{style['outline']},{style['shadow']},2,40,40,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def create_karaoke_dialogue(chunk: Dict, style_key: str) -> str:
    """
    Create ASS dialogue line with karaoke effect.
    Uses \k tags for word-by-word highlighting.
    """
    style = SUBTITLE_STYLES.get(style_key, SUBTITLE_STYLES["tiktok"])

    start_time = format_ass_time(chunk['start_ms'])
    end_time = format_ass_time(chunk['end_ms'])

    # Build karaoke text with \k tags
    # \k<duration> sets highlight timing in centiseconds
    karaoke_parts = []

    # Add fade in animation
    fade_in = CONFIG['fade_in_ms']
    fade_out = CONFIG['fade_out_ms']

    for i, wt in enumerate(chunk['words']):
        word = wt['word'].upper()  # Uppercase for impact

        # Calculate duration in centiseconds
        duration_cs = max(1, (wt['end_ms'] - wt['start_ms']) // 10)

        # Use \kf for smooth fill effect (karaoke fill)
        karaoke_parts.append(f"{{\\kf{duration_cs}}}{word}")

    karaoke_text = ' '.join(karaoke_parts)

    # Add animation: fade + slight scale pop
    # \fad(fadein,fadeout) \t(t1,t2,\fscx\fscy) for scale animation
    animation = f"{{\\fad({fade_in},{fade_out})}}"

    return f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{animation}{karaoke_text}"


def create_simple_dialogue(chunk: Dict, style_key: str) -> str:
    """
    Create simple ASS dialogue without karaoke (fallback).
    """
    start_time = format_ass_time(chunk['start_ms'])
    end_time = format_ass_time(chunk['end_ms'])

    text = chunk['text'].upper()

    # Split into 2 lines if too long
    words = text.split()
    if len(words) > 3:
        mid = len(words) // 2
        text = ' '.join(words[:mid]) + '\\N' + ' '.join(words[mid:])

    fade_in = CONFIG['fade_in_ms']
    fade_out = CONFIG['fade_out_ms']

    return f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\fad({fade_in},{fade_out})}}{text}"


def transcript_to_karaoke_ass(transcript: List[Dict], style_key: str = "tiktok", use_karaoke: bool = True) -> str:
    """
    Convert transcript to ASS format with karaoke effects.
    """
    ass_content = generate_ass_header(style_key)

    all_word_timestamps = []

    # Extract word timestamps from all segments
    for segment in transcript:
        word_ts = estimate_word_timestamps(segment)
        all_word_timestamps.extend(word_ts)

    # Create chunks
    chunks = create_chunks(all_word_timestamps)

    # Generate dialogue lines
    for chunk in chunks:
        if use_karaoke and len(chunk['words']) > 1:
            dialogue = create_karaoke_dialogue(chunk, style_key)
        else:
            dialogue = create_simple_dialogue(chunk, style_key)
        ass_content += dialogue + "\n"

    return ass_content


def create_subtitle_file(transcript: List[Dict], output_path: str, style_key: str = "tiktok") -> bool:
    """Create an ASS subtitle file from transcript."""
    try:
        ass_content = transcript_to_karaoke_ass(transcript, style_key, use_karaoke=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        return True
    except Exception as e:
        print(f"Error creating subtitle file: {e}")
        return False


def burn_subtitles(input_video: str, output_video: str, subtitle_file: str, style_key: str = "tiktok") -> Dict:
    """Burn subtitles into video using ffmpeg with ASS filter."""
    try:
        # Escape path for ffmpeg filter
        sub_path = subtitle_file.replace('\\', '/').replace(':', '\\:').replace("'", "\\'")

        # Use ASS filter for proper rendering of karaoke effects
        cmd = [
            'ffmpeg',
            '-y',
            '-i', input_video,
            '-vf', f"ass='{sub_path}'",
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '22',
            output_video
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            # Try subtitles filter as fallback
            cmd_fallback = [
                'ffmpeg',
                '-y',
                '-i', input_video,
                '-vf', f"subtitles='{sub_path}'",
                '-c:a', 'copy',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '22',
                output_video
            ]
            result = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                return {'success': False, 'error': f'FFmpeg error: {result.stderr[:500]}'}

        return {'success': True}

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Subtitle burning timed out'}
    except FileNotFoundError:
        return {'success': False, 'error': 'ffmpeg not found. Please install ffmpeg.'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_transcript_segment(full_transcript: List[Dict], start_time: int, end_time: int) -> List[Dict]:
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


def get_available_styles() -> Dict:
    """Return available subtitle styles."""
    return {
        key: {
            "name": style["name"],
            "highlight_color": style["highlight_color"],
        }
        for key, style in SUBTITLE_STYLES.items()
    }
