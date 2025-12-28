#!/usr/bin/env python3
"""
FOIA-BOT for Colab with OpenRouter LLM Support
Complete solution with scaffolded prompts
"""

# ============================================
# 📝 CONFIGURATION
# ============================================

# Case details
YOUTUBE_URL = "https://www.youtube.com/watch?v=IxvpMvvY6ig"
DEFENDANT_NAME = "Charles Liggins"  # Use primary defendant only!
CASE_DESC = "FBG Duck murder case"

# LLM Configuration (OpenRouter recommended - cheapest & best)
USE_LLM = True  # Enable LLM fallback for transcript processing

# OpenRouter API Key (get free credits at: https://openrouter.ai/)
OPENROUTER_API_KEY = ""  # ← ADD YOUR KEY HERE

# Model selection (recommended: "cheap" for best value)
# Options: "cheap" (Haiku ~$0.0003/video), "quality" (Sonnet ~$0.0045/video)
LLM_TIER = "cheap"  # ← "cheap" or "quality"

# CourtListener API (optional - for court docs)
COURTLISTENER_KEY = ""  # ← Optional

# ============================================
# 🚀 PROCESSING CODE
# ============================================

TRANSCRIPT_ANALYSIS_PROMPT = """You are a legal transcript analyst helping with investigative journalism.

<task>
Analyze this criminal case video transcript and extract structured information about:
1. Defendant names and key people
2. Time segments where court proceedings are discussed
3. Time segments where police evidence (bodycam, 911, interrogations) is discussed
4. Key topics and themes
</task>

<instructions>
Think step-by-step:
1. First, read through and identify all person names mentioned
2. Then, scan for any timestamps or time markers in the transcript
3. Categorize segments by content type (court/FOIA/general)
4. Extract key themes and topics
</instructions>

<examples>
Example 1 - Court Segment:
"At 5 minutes 30 seconds, the narrator discusses the indictment, stating that the defendant was charged with first-degree murder..."
→ Classification: COURT segment from 00:05:30 to ~00:06:00

Example 2 - FOIA Segment:
"The bodycam footage, shown at the 12-minute mark, reveals the moment of arrest..."
→ Classification: FOIA segment from 00:12:00 to ~00:13:00
</examples>

<transcript>
{transcript_text}
</transcript>

<output_format>
Return ONLY valid JSON:

{{
  "reasoning": "Brief explanation of what you found",
  "defendants": [
    {{"name": "Primary Defendant", "role": "defendant"}}
  ],
  "court_segments": [
    {{
      "start_time": "00:05:30",
      "end_time": "00:08:45",
      "topic": "Indictment and charges",
      "keywords": ["indictment", "charges"]
    }}
  ],
  "foia_segments": [
    {{
      "start_time": "00:12:00",
      "end_time": "00:15:30",
      "topic": "Bodycam footage",
      "keywords": ["bodycam", "arrest"]
    }}
  ],
  "key_topics": [
    {{"topic": "Murder charges", "importance": "high"}}
  ],
  "summary": "One-sentence case summary"
}}
</output_format>

<guidelines>
- If no timestamps exist, estimate based on content order
- Use "00:00:00" format
- Be conservative - only mark segments if clearly court/FOIA related
</guidelines>

Return JSON:"""


def process_with_openrouter(transcript_text, api_key, tier="cheap"):
    """Process transcript using OpenRouter"""
    import requests
    import json
    import re

    # Model selection
    models = {
        "cheap": "anthropic/claude-3-haiku",  # $0.25/M tokens
        "quality": "anthropic/claude-3.5-sonnet",  # $3/M tokens
    }
    model = models.get(tier, models["cheap"])

    # Truncate if too long (save costs)
    max_chars = 15000
    if len(transcript_text) > max_chars:
        print(f"⚠️  Truncating transcript: {len(transcript_text)} → {max_chars} chars")
        transcript_text = transcript_text[:max_chars]

    # Build prompt
    prompt = TRANSCRIPT_ANALYSIS_PROMPT.format(
        transcript_text=transcript_text
    )

    print(f"🤖 Calling OpenRouter with {model}")
    print(f"   Prompt: {len(prompt)} chars")
    print(f"   Est. cost: ~$0.0003")

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/yourusername/FOIA-BOT",
                "X-Title": "FOIA-BOT",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.3,
            },
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        result_text = data['choices'][0]['message']['content']
        print(f"✅ Received response: {len(result_text)} chars")

        # Extract JSON
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(1)

        result = json.loads(result_text)

        # Show what we found
        print(f"\n📊 LLM Analysis:")
        print(f"   Defendants: {[d['name'] for d in result.get('defendants', [])]}")
        print(f"   Court segments: {len(result.get('court_segments', []))}")
        print(f"   FOIA segments: {len(result.get('foia_segments', []))}")
        print(f"   Summary: {result.get('summary', 'N/A')}")

        return result

    except Exception as e:
        print(f"❌ OpenRouter error: {e}")
        return None


def time_to_seconds(time_str):
    """Convert HH:MM:SS to seconds"""
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


def llm_result_to_cues(llm_result):
    """Convert LLM output to cues.json format"""
    if not llm_result:
        return []

    cues = []

    # Add court segments
    for seg in llm_result.get('court_segments', []):
        start = time_to_seconds(seg.get('start_time'))
        end = time_to_seconds(seg.get('end_time'))
        if start and end and end > start:
            cues.append({
                'start': round(start, 2),
                'end': round(end, 2),
                'bucket': 'court'
            })

    # Add FOIA segments
    for seg in llm_result.get('foia_segments', []):
        start = time_to_seconds(seg.get('start_time'))
        end = time_to_seconds(seg.get('end_time'))
        if start and end and end > start:
            cues.append({
                'start': round(start, 2),
                'end': round(end, 2),
                'bucket': 'foia'
            })

    # Sort by time
    cues.sort(key=lambda x: x['start'])

    return cues


# ============================================
# MAIN COLAB SCRIPT
# ============================================

def run_foia_bot():
    import os, json, re, subprocess, shutil
    from pathlib import Path
    from datetime import datetime

    # Mount & install
    print("📁 Setting up...")
    os.chdir('/content')

    from google.colab import drive
    drive.mount('/content/drive')

    get_ipython().system('pip install -q yt-dlp requests beautifulsoup4 feedparser newspaper3k lxml_html_clean pandas matplotlib')

    # Setup repo
    repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')
    if (repo_dir / '.git').exists():
        os.chdir(str(repo_dir))
        get_ipython().system('git pull --quiet')
    elif not (repo_dir / 'video_ingest.py').exists():
        get_ipython().system(f'git clone https://github.com/jj55222/FOIA-BOT.git {str(repo_dir)}')

    # Create case directory
    match = re.search(r'v=([a-zA-Z0-9_-]+)', YOUTUBE_URL)
    video_id = match.group(1) if match else "case"
    case_name = f"case_{datetime.now().strftime('%Y%m%d')}_{video_id}"
    case_dir = repo_dir / case_name
    case_dir.mkdir(exist_ok=True)
    os.chdir(str(case_dir))

    # Set API keys
    if COURTLISTENER_KEY:
        os.environ['COURTLISTENER_API_KEY'] = COURTLISTENER_KEY
    if OPENROUTER_API_KEY:
        os.environ['OPENROUTER_API_KEY'] = OPENROUTER_API_KEY

    print("="*60)
    print(f"🎯 Case: {DEFENDANT_NAME}")
    print(f"📁 {case_name}")
    if USE_LLM and OPENROUTER_API_KEY:
        print(f"🤖 LLM: Enabled ({LLM_TIER} tier)")
    print("="*60)

    # ============================================
    # Step 1: Download Video & Get Transcript
    # ============================================
    print("\n📥 Step 1: Video Download")
    print("-"*60)

    subprocess.run(
        f'python3 "{repo_dir}/video_ingest.py" "{YOUTUBE_URL}"',
        shell=True, cwd=str(case_dir)
    )

    # Find transcript
    transcript = case_dir / 'transcript.vtt'
    if not transcript.exists():
        vtt_files = list(case_dir.glob('*.vtt'))
        if vtt_files:
            shutil.copy2(vtt_files[0], transcript)
            print(f"✅ Transcript: {vtt_files[0].name}")

    # ============================================
    # Step 2: Process Transcript with LLM
    # ============================================
    print("\n🏷️  Step 2: Transcript Processing")
    print("-"*60)

    if not transcript.exists():
        print("❌ No transcript - skipping")
    else:
        with open(transcript, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

        print(f"📄 Transcript: {len(transcript_text)} chars")

        # Try LLM processing
        if USE_LLM and OPENROUTER_API_KEY:
            llm_result = process_with_openrouter(
                transcript_text,
                OPENROUTER_API_KEY,
                LLM_TIER
            )

            if llm_result:
                # Convert to cues
                cues = llm_result_to_cues(llm_result)

                # Save cues.json
                with open(case_dir / 'cues.json', 'w') as f:
                    json.dump(cues, f, indent=2)

                print(f"\n✅ Created {len(cues)} cues from LLM analysis")

                # Get defendant names from LLM
                llm_defendants = [d['name'] for d in llm_result.get('defendants', [])]
                if llm_defendants:
                    print(f"   Defendants found: {', '.join(llm_defendants)}")
                    # Use these for searches
                    global DEFENDANT_NAME
                    if not DEFENDANT_NAME:
                        DEFENDANT_NAME = llm_defendants[0]
            else:
                print("⚠️  LLM processing failed")
        else:
            print("ℹ️  LLM processing disabled (no API key or USE_LLM=False)")

    # ============================================
    # Steps 3-6: Court, FOIA, News, Package
    # ============================================

    print(f"\n⚖️  Step 3: Court Documents - {DEFENDANT_NAME}")
    print("-"*60)
    subprocess.run(
        f'python3 "{repo_dir}/court_docs.py" "{DEFENDANT_NAME}"',
        shell=True, cwd=str(case_dir)
    )

    print(f"\n🎥 Step 4: FOIA Media")
    print("-"*60)
    subprocess.run(
        f'python3 "{repo_dir}/foia_media_scraper.py"',
        shell=True, cwd=str(case_dir)
    )

    print(f"\n📰 Step 5: News Articles")
    print("-"*60)
    for term in [DEFENDANT_NAME, f"{DEFENDANT_NAME} trial"]:
        subprocess.run(
            f'python3 "{repo_dir}/news_scraper.py" "{term}"',
            shell=True, cwd=str(case_dir)
        )

    print(f"\n📦 Step 6: Creating Bundle")
    print("-"*60)
    subprocess.run(
        f'python3 "{repo_dir}/packager.py"',
        shell=True, cwd=str(case_dir)
    )

    # ============================================
    # Summary
    # ============================================
    print("\n" + "="*60)
    print("✅ PROCESSING COMPLETE!")
    print("="*60)

    bundle = case_dir / f"{case_name}_bundle.zip"
    if bundle.exists():
        size = bundle.stat().st_size / (1024*1024)
        print(f"\n📦 Bundle: {size:.2f} MB")

        for subdir in ['court_docs', 'media', 'news']:
            path = case_dir / subdir
            if path.exists():
                count = len(list(path.iterdir()))
                print(f"   {subdir}: {count} files")

        # Show cues stats
        cues_file = case_dir / 'cues.json'
        if cues_file.exists():
            with open(cues_file) as f:
                cues = json.load(f)
            buckets = {}
            for cue in cues:
                dur = cue['end'] - cue['start']
                buckets[cue['bucket']] = buckets.get(cue['bucket'], 0) + dur

            if buckets:
                print(f"\n📊 Video buckets:")
                for bucket, dur in buckets.items():
                    print(f"   {bucket}: {dur:.1f}s")

        print(f"\n🎯 {DEFENDANT_NAME} - {CASE_DESC}")
        print(f"📁 MyDrive/foia_bot/repo/{case_name}/")


# ============================================
# RUN IT!
# ============================================
if __name__ == '__main__':
    run_foia_bot()
