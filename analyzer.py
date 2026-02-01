"""
YouTube Gaming Clip Analyzer
Fetches transcripts and uses Claude to detect clipworthy moments.
"""

import json
import re
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import anthropic


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_transcript(video_id: str) -> dict:
    """
    Fetch transcript for a YouTube video.
    Returns dict with 'success', 'transcript' or 'error' keys.
    """
    try:
        api = YouTubeTranscriptApi()

        # Try to fetch with multiple language preferences
        languages = ['en', 'en-US', 'en-GB', 'fr', 'es', 'de']
        fetched = api.fetch(video_id, languages=languages)

        # Convert to list of dicts format
        transcript = [
            {'start': snippet.start, 'duration': snippet.duration, 'text': snippet.text}
            for snippet in fetched
        ]

        return {
            'success': True,
            'transcript': transcript,
            'video_id': video_id
        }
    except TranscriptsDisabled:
        return {'success': False, 'error': 'Transcripts are disabled for this video'}
    except NoTranscriptFound:
        return {'success': False, 'error': 'No transcript found for this video'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def format_transcript_for_analysis(transcript: list) -> str:
    """Format transcript entries with timestamps for Claude analysis."""
    formatted_lines = []
    for entry in transcript:
        start = entry['start']
        minutes = int(start // 60)
        seconds = int(start % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        text = entry['text'].strip()
        formatted_lines.append(f"{timestamp} {text}")
    return "\n".join(formatted_lines)


def analyze_with_claude(transcript: list, api_key: str) -> dict:
    """
    Send transcript to Claude for gaming moment analysis.
    Returns dict with 'success' and 'clips' or 'error'.
    """
    client = anthropic.Anthropic(api_key=api_key)

    formatted_transcript = format_transcript_for_analysis(transcript)

    # Calculate video duration from last transcript entry
    if transcript:
        video_duration = transcript[-1]['start'] + transcript[-1].get('duration', 5)
    else:
        video_duration = 0

    system_prompt = """You are an expert gaming content analyst specializing in identifying viral-worthy clip moments from gaming streams and videos.

Your task is to analyze video transcripts and identify the BEST moments that would make engaging short-form clips (15-60 seconds).

You detect moments based on:

1. **EMOTIONAL INTENSITY** - Look for:
   - Rage moments (frustration, anger, disbelief at failures)
   - Hype moments (excitement, celebration, adrenaline)
   - Surprise/shock reactions
   - Genuine laughter or comedic moments

2. **GAMING KEYWORDS & PHRASES** - Watch for:
   - Expressions: "wtf", "what the f***", "no way", "insane", "let's go", "oh my god", "gg", "ez", "clutch"
   - Victory/defeat reactions: "we won", "I did it", "noooo", "how", "impossible"
   - Skill callouts: "headshot", "one tap", "ace", "penta", "combo", "perfect"

3. **CONTEXT CLUES** - Consider:
   - Build-up moments that lead to climax
   - Repeated emphasis or intensity
   - Tonal shifts (calm to excited, confident to shocked)

SCORING CRITERIA (1-10):
- 9-10: Guaranteed viral potential, extremely intense/funny/impressive
- 7-8: Very strong clip, highly engaging
- 5-6: Good clip, solid content
- 3-4: Decent moment but not standout
- 1-2: Minor moment, probably skip

OUTPUT FORMAT: Return ONLY valid JSON array, no markdown formatting, no code blocks."""

    user_prompt = f"""Analyze this gaming video transcript and identify the TOP 5-8 best moments to clip.

VIDEO DURATION: {int(video_duration)} seconds

TRANSCRIPT:
{formatted_transcript}

For each moment, provide:
- start_time: timestamp in seconds (integer)
- end_time: suggested clip end in seconds (clip should be 15-60 seconds)
- score: 1-10 rating
- category: one of ["hype", "rage", "funny", "clutch", "fail", "reaction", "skill"]
- reason: brief explanation why this moment is clipworthy (1-2 sentences)
- suggested_title: catchy, short title for the clip (gaming/meme style)

Return a JSON array of objects sorted by score (highest first). Include 5-8 moments.

Example format:
[
  {{
    "start_time": 125,
    "end_time": 155,
    "score": 9,
    "category": "hype",
    "reason": "Intense reaction to winning with extreme hype and celebration",
    "suggested_title": "THE CRAZIEST CLUTCH EVER 🔥"
  }}
]

Return ONLY the JSON array, nothing else."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            system=system_prompt
        )

        # Extract text content
        content = response.content[0].text.strip()

        # Try to parse JSON (handle potential markdown code blocks)
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\n?', '', content)
            content = re.sub(r'\n?```$', '', content)

        clips = json.loads(content)

        # Validate and clean up clips
        validated_clips = []
        for clip in clips:
            if all(key in clip for key in ['start_time', 'end_time', 'score', 'category', 'reason', 'suggested_title']):
                clip['start_time'] = int(clip['start_time'])
                clip['end_time'] = int(clip['end_time'])
                clip['score'] = min(10, max(1, clip['score']))
                validated_clips.append(clip)

        # Sort by score descending
        validated_clips.sort(key=lambda x: x['score'], reverse=True)

        return {
            'success': True,
            'clips': validated_clips[:8],
            'video_duration': int(video_duration)
        }

    except json.JSONDecodeError as e:
        return {'success': False, 'error': f'Failed to parse Claude response as JSON: {str(e)}'}
    except anthropic.APIError as e:
        return {'success': False, 'error': f'Anthropic API error: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Analysis error: {str(e)}'}


def analyze_video(url: str, api_key: str) -> dict:
    """
    Main function: analyze a YouTube video for clipworthy moments.
    Returns full analysis result.
    """
    # Extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        return {'success': False, 'error': 'Invalid YouTube URL'}

    # Fetch transcript
    transcript_result = fetch_transcript(video_id)
    if not transcript_result['success']:
        return transcript_result

    # Analyze with Claude
    analysis_result = analyze_with_claude(transcript_result['transcript'], api_key)

    if analysis_result['success']:
        analysis_result['video_id'] = video_id
        analysis_result['video_url'] = f"https://www.youtube.com/watch?v={video_id}"

    return analysis_result
