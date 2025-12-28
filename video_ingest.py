#!/usr/bin/env python3
"""
Video ingest script: Downloads YouTube video and creates bucket-tagged cues.json
Uses free YouTube auto-captions when available, with optional whisper fallback.
"""

import subprocess
import sys
import json
import os
import re
from pathlib import Path
from datetime import datetime


def download_video_and_captions(youtube_url, output_dir):
    """Download video and try to get YouTube auto-captions"""
    print(f"📥 Downloading video from: {youtube_url}")

    # Try to download with auto-generated subtitles first
    cmd = [
        'yt-dlp',
        '--write-auto-subs',
        '--sub-lang', 'en',
        '--convert-subs', 'vtt',
        '--output', str(output_dir / 'raw_video.%(ext)s'),
        youtube_url
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Video downloaded successfully")

        # Find the downloaded files
        video_file = None
        vtt_file = None

        for f in output_dir.iterdir():
            if f.name.startswith('raw_video.') and f.suffix in ['.mp4', '.mkv', '.webm']:
                video_file = f
            elif f.suffix == '.vtt':
                vtt_file = f

        return video_file, vtt_file

    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading video: {e}")
        if e.stderr:
            print(f"\nyt-dlp error output:")
            print(e.stderr)
        if e.stdout:
            print(f"\nyt-dlp output:")
            print(e.stdout)
        print("\n💡 Common issues:")
        print("   - Video may be private or age-restricted")
        print("   - Check your internet connection")
        print("   - Ensure yt-dlp is up to date: pip install -U yt-dlp")
        sys.exit(1)


def parse_vtt_to_segments(vtt_file):
    """Parse VTT file into time-segmented text"""
    if not vtt_file or not vtt_file.exists():
        print("⚠️  No VTT captions found")
        return []

    print(f"📝 Parsing captions from: {vtt_file}")

    segments = []
    with open(vtt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse VTT format: timestamp --> timestamp followed by text
    pattern = r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*\n(.*?)(?=\n\n|\Z)'
    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        start_h, start_m, start_s, start_ms = map(int, match.groups()[:4])
        end_h, end_m, end_s, end_ms = map(int, match.groups()[4:8])
        text = match.group(9).strip()

        start_seconds = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
        end_seconds = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000

        # Clean up text (remove formatting tags)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('\n', ' ').strip()

        if text:
            segments.append({
                'start': start_seconds,
                'end': end_seconds,
                'text': text
            })

    print(f"✅ Parsed {len(segments)} caption segments")
    return segments


def bucket_tag_segments(segments):
    """Tag segments with buckets based on keyword heuristics"""

    # Ultra-cheap heuristic keywords
    court_keywords = [
        'count i', 'count ii', 'count iii', 'indictment', 'arraignment',
        'life without parole', 'guilty', 'sentenc', 'conviction', 'verdict',
        'plaintiff', 'defendant', 'prosecution', 'defense attorney', 'judge',
        'jury', 'court', 'trial', 'testimony', 'evidence', 'objection'
    ]

    foia_keywords = [
        'body-cam', 'bodycam', 'body cam', 'dashcam', 'dash-cam', 'dash cam',
        '911 audio', 'police footage', 'surveillance', 'cctv', 'security camera',
        'interrogation', 'interview room', 'dispatch', 'officer', 'badge'
    ]

    cues = []

    for seg in segments:
        text_lower = seg['text'].lower()
        bucket = 'secondary'  # default

        # Check for court keywords
        if any(kw in text_lower for kw in court_keywords):
            bucket = 'court'
        # Check for FOIA keywords
        elif any(kw in text_lower for kw in foia_keywords):
            bucket = 'foia'

        cues.append({
            'start': round(seg['start'], 2),
            'end': round(seg['end'], 2),
            'bucket': bucket,
            'text': seg['text']  # Include text for reference
        })

    return cues


def merge_adjacent_buckets(cues, max_gap=5.0):
    """Merge adjacent segments with the same bucket to reduce granularity"""
    if not cues:
        return []

    merged = [cues[0].copy()]

    for cue in cues[1:]:
        last = merged[-1]

        # If same bucket and close in time, merge
        if (cue['bucket'] == last['bucket'] and
            cue['start'] - last['end'] <= max_gap):
            last['end'] = cue['end']
            last['text'] += ' ' + cue['text']
        else:
            merged.append(cue.copy())

    return merged


def save_cues(cues, output_file):
    """Save cues to JSON file"""
    # Simplify output (remove text field for final cues.json)
    simplified_cues = [
        {
            'start': c['start'],
            'end': c['end'],
            'bucket': c['bucket']
        }
        for c in cues
    ]

    with open(output_file, 'w') as f:
        json.dump(simplified_cues, f, indent=2)

    print(f"✅ Saved {len(simplified_cues)} cues to {output_file}")

    # Print summary
    buckets = {}
    total_time = 0
    for c in simplified_cues:
        duration = c['end'] - c['start']
        buckets[c['bucket']] = buckets.get(c['bucket'], 0) + duration
        total_time += duration

    print("\n📊 Bucket summary:")
    for bucket, duration in sorted(buckets.items()):
        percentage = (duration / total_time * 100) if total_time > 0 else 0
        print(f"  {bucket}: {duration:.1f}s ({percentage:.1f}%)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python video_ingest.py <youtube_url>")
        print("Note: Run this from inside a case_YYYYMMDD_<slug>/ directory")
        sys.exit(1)

    youtube_url = sys.argv[1]
    output_dir = Path.cwd()

    print(f"🎬 FOIA-BOT Video Ingest")
    print(f"Working directory: {output_dir}")
    print(f"YouTube URL: {youtube_url}\n")

    # Download video and captions
    video_file, vtt_file = download_video_and_captions(youtube_url, output_dir)

    if not vtt_file:
        print("\n⚠️  No auto-captions available from YouTube")
        print("💡 To use local whisper fallback, install openai-whisper and uncomment the fallback code")
        sys.exit(1)

    # Rename VTT to standard name
    transcript_path = output_dir / 'transcript.vtt'
    if vtt_file != transcript_path:
        vtt_file.rename(transcript_path)
        print(f"📝 Renamed captions to: transcript.vtt")

    # Parse captions
    segments = parse_vtt_to_segments(transcript_path)

    if not segments:
        print("❌ No segments extracted from captions")
        sys.exit(1)

    # Tag with buckets
    print("\n🏷️  Tagging segments with buckets...")
    cues = bucket_tag_segments(segments)

    # Merge adjacent same-bucket segments
    print("🔗 Merging adjacent segments...")
    merged_cues = merge_adjacent_buckets(cues)

    # Save cues.json
    cues_file = output_dir / 'cues.json'
    save_cues(merged_cues, cues_file)

    print("\n✅ Video ingest complete!")


if __name__ == '__main__':
    main()
