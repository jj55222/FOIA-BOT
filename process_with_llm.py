#!/usr/bin/env python3
"""
FOIA-BOT with LLM-powered Processing
Hybrid approach: Try regex, fall back to LLM when needed
"""

import os
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

# ============================================
# LLM-Powered Transcript Processing
# ============================================

def process_transcript_with_llm(transcript_text, api_key=None):
    """
    Use Claude API to intelligently process transcript
    Extracts names, creates time-bucketed content categories
    """
    import anthropic

    if not api_key:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("⚠️  No ANTHROPIC_API_KEY found. Skipping LLM processing.")
            return None

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Analyze this video transcript and extract the following in JSON format:

1. Defendant names (primary people charged/on trial)
2. Court-related time segments (when legal proceedings are discussed)
3. FOIA-related time segments (when police footage, 911 calls, interrogations, etc. are discussed)
4. Key topics and themes

Transcript:
{transcript_text[:15000]}  # First ~15k chars to stay within limits

Return ONLY valid JSON in this exact format:
{{
  "defendants": ["Name 1", "Name 2"],
  "court_segments": [
    {{"start_time": "00:05:30", "end_time": "00:08:45", "topic": "Indictment reading"}}
  ],
  "foia_segments": [
    {{"start_time": "00:12:00", "end_time": "00:15:30", "topic": "Bodycam footage discussion"}}
  ],
  "key_topics": ["Topic 1", "Topic 2"]
}}

If no timestamps are available, use estimated times or null.
"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)

        result = json.loads(response_text)
        return result

    except Exception as e:
        print(f"⚠️  LLM processing failed: {e}")
        return None


def convert_llm_segments_to_cues(llm_result):
    """Convert LLM output to cues.json format"""
    if not llm_result:
        return []

    cues = []

    def time_to_seconds(time_str):
        """Convert HH:MM:SS or MM:SS to seconds"""
        if not time_str:
            return 0
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = map(float, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(float, parts)
            return m * 60 + s
        return 0

    # Add court segments
    for seg in llm_result.get('court_segments', []):
        start = time_to_seconds(seg.get('start_time'))
        end = time_to_seconds(seg.get('end_time'))
        if start and end:
            cues.append({
                'start': round(start, 2),
                'end': round(end, 2),
                'bucket': 'court'
            })

    # Add FOIA segments
    for seg in llm_result.get('foia_segments', []):
        start = time_to_seconds(seg.get('start_time'))
        end = time_to_seconds(seg.get('end_time'))
        if start and end:
            cues.append({
                'start': round(start, 2),
                'end': round(end, 2),
                'bucket': 'foia'
            })

    # Sort by start time
    cues.sort(key=lambda x: x['start'])

    return cues


# ============================================
# Improved VTT Parser
# ============================================

def parse_vtt_robust(vtt_file):
    """More robust VTT parser that handles multiple formats"""
    with open(vtt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    cues = []

    # Try multiple timestamp formats
    patterns = [
        # Standard: 00:00:00.000 --> 00:00:05.000
        r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*\n(.*?)(?=\n\n|\n\d|\Z)',
        # Short: 00:00.000 --> 00:05.000
        r'(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2})\.(\d{3})\s*\n(.*?)(?=\n\n|\n\d|\Z)',
        # With sequence numbers
        r'\d+\n(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*\n(.*?)(?=\n\n|\Z)',
    ]

    for pattern in patterns:
        matches = list(re.finditer(pattern, content, re.DOTALL))
        if matches:
            print(f"✅ Matched VTT format with pattern {patterns.index(pattern) + 1}")

            for m in matches:
                groups = m.groups()

                # Handle different group counts
                if len(groups) == 9:  # Full timestamp
                    start_h, start_m, start_s, start_ms = map(int, groups[:4])
                    end_h, end_m, end_s, end_ms = map(int, groups[4:8])
                    text = groups[8]
                elif len(groups) == 7:  # Short timestamp
                    start_h = 0
                    start_m, start_s, start_ms = map(int, groups[:3])
                    end_h = 0
                    end_m, end_s, end_ms = map(int, groups[3:6])
                    text = groups[6]
                else:
                    continue

                start = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
                end = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000

                text = re.sub(r'<[^>]+>', '', text).replace('\n', ' ').strip()

                if text:
                    cues.append({
                        'start': start,
                        'end': end,
                        'text': text.lower()
                    })

            return cues

    print("⚠️  No VTT patterns matched")
    return []


def bucket_cues(cues):
    """Assign buckets based on keywords"""
    court_kw = ['count', 'indictment', 'guilty', 'sentence', 'trial',
                'murder', 'charge', 'convicted', 'verdict', 'jury']

    foia_kw = ['bodycam', '911', 'surveillance', 'interrogation',
               'officer', 'detective', 'arrest']

    for cue in cues:
        text = cue.get('text', '')
        cue['bucket'] = 'secondary'

        if any(kw in text for kw in court_kw):
            cue['bucket'] = 'court'
        elif any(kw in text for kw in foia_kw):
            cue['bucket'] = 'foia'

    return cues


def merge_adjacent_cues(cues, max_gap=5.0):
    """Merge adjacent same-bucket segments"""
    if not cues:
        return []

    merged = [cues[0].copy()]
    for cue in cues[1:]:
        last = merged[-1]
        if (cue['bucket'] == last['bucket'] and
            cue['start'] - last['end'] <= max_gap):
            last['end'] = cue['end']
        else:
            merged.append(cue.copy())

    # Remove 'text' field for final output
    for cue in merged:
        cue.pop('text', None)

    return merged


# ============================================
# Main Processing Function
# ============================================

def process_case_hybrid(case_dir, repo_dir, use_llm=True, anthropic_key=None):
    """
    Hybrid processing: Try regex, fall back to LLM

    Args:
        case_dir: Path to case directory
        repo_dir: Path to FOIA-BOT repo
        use_llm: Whether to use LLM fallback if regex fails
        anthropic_key: Anthropic API key (optional)
    """
    transcript_file = case_dir / 'transcript.vtt'
    cues_file = case_dir / 'cues.json'

    if not transcript_file.exists():
        print("❌ No transcript.vtt found")
        return None, None

    # Read transcript
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript_text = f.read()

    print(f"📄 Transcript: {len(transcript_text)} chars")

    # Step 1: Try robust VTT parsing
    print("\n🔧 Attempting VTT parsing...")
    cues = parse_vtt_robust(transcript_file)

    if cues:
        print(f"✅ Parsed {len(cues)} segments from VTT")
        cues = bucket_cues(cues)
        cues = merge_adjacent_cues(cues)

        # Save cues
        with open(cues_file, 'w') as f:
            json.dump(cues, f, indent=2)

        print(f"✅ Created {len(cues)} cues via regex parsing")

        # Extract names from VTT text
        defendants = extract_names_simple(transcript_text)

        return cues, defendants

    # Step 2: Fall back to LLM if VTT parsing failed
    if use_llm and len(cues) == 0:
        print("\n🤖 VTT parsing failed. Trying LLM processing...")

        llm_result = process_transcript_with_llm(transcript_text, anthropic_key)

        if llm_result:
            print("✅ LLM processing successful")
            print(f"   Defendants: {llm_result.get('defendants', [])}")
            print(f"   Court segments: {len(llm_result.get('court_segments', []))}")
            print(f"   FOIA segments: {len(llm_result.get('foia_segments', []))}")

            cues = convert_llm_segments_to_cues(llm_result)

            if cues:
                with open(cues_file, 'w') as f:
                    json.dump(cues, f, indent=2)
                print(f"✅ Created {len(cues)} cues via LLM")

            defendants = llm_result.get('defendants', [])

            return cues, defendants

    print("⚠️  Both VTT parsing and LLM processing failed")
    return [], []


def extract_names_simple(text):
    """Simple name extraction from text"""
    # Look for "v." pattern
    pattern = r'(?:State|People|United States)\s+v\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
    matches = re.findall(pattern, text, re.IGNORECASE)

    names = [m.strip() for m in matches if len(m.strip()) > 5]
    return list(set(names))[:3]  # Max 3 names


# ============================================
# CLI Usage
# ============================================

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python process_with_llm.py <case_directory> [--use-llm] [--api-key KEY]")
        sys.exit(1)

    case_dir = Path(sys.argv[1])
    use_llm = '--use-llm' in sys.argv

    api_key = None
    if '--api-key' in sys.argv:
        idx = sys.argv.index('--api-key')
        api_key = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None

    repo_dir = case_dir.parent

    cues, defendants = process_case_hybrid(case_dir, repo_dir, use_llm, api_key)

    print(f"\n✅ Processing complete")
    print(f"   Cues: {len(cues)}")
    print(f"   Defendants: {defendants}")
