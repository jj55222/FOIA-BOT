#!/usr/bin/env python3
"""
FOIA-BOT New Case Template for Google Colab
Customize the variables below for your case
"""

# ============================================
# 📝 CONFIGURE YOUR CASE HERE
# ============================================

# YouTube video URL
YOUTUBE_URL = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"  # ← CHANGE THIS!

# Defendant/Subject name
DEFENDANT_NAME = "Firstname Lastname"  # ← CHANGE THIS!

# Additional search terms for news
NEWS_SEARCH_TERMS = [
    "Firstname Lastname murder trial",
    "Firstname Lastname case",
    "State v Firstname Lastname"
]  # ← CUSTOMIZE THESE!

# Case description (for documentation)
CASE_DESCRIPTION = "Brief description of the case"  # ← CHANGE THIS!

# CourtListener API Key (optional - get from https://www.courtlistener.com/sign-in/)
COURTLISTENER_API_KEY = ""  # ← OPTIONAL: Add your API key here

# ============================================
# 🚀 PROCESSING CODE (No need to modify)
# ============================================

import os
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

def run_colab_case():
    """Run complete FOIA-BOT pipeline in Colab"""

    # Set up environment
    import os
    os.chdir('/content')

    # Mount Drive
    print("📁 Mounting Google Drive...")
    from google.colab import drive
    drive.mount('/content/drive')

    # Install dependencies
    print("\n📦 Installing dependencies...")
    get_ipython().system('pip install -q yt-dlp requests beautifulsoup4 feedparser newspaper3k lxml_html_clean pandas matplotlib')

    # Set up paths
    repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')

    # Clone repo if needed
    if not (repo_dir / 'video_ingest.py').exists():
        print("\n📥 Cloning FOIA-BOT...")
        get_ipython().system(f'git clone https://github.com/jj55222/FOIA-BOT.git {str(repo_dir)}')
    else:
        # Pull latest changes
        os.chdir(str(repo_dir))
        get_ipython().system('git pull')

    # Extract video ID for case directory
    match = re.search(r'v=([a-zA-Z0-9_-]+)', YOUTUBE_URL)
    video_id = match.group(1) if match else "video"
    case_name = f"case_{datetime.now().strftime('%Y%m%d')}_{video_id}"
    case_dir = repo_dir / case_name

    print(f"\n{'='*60}")
    print(f"🎯 Case: {DEFENDANT_NAME}")
    print(f"📺 Video: {YOUTUBE_URL}")
    print(f"📁 Directory: {case_name}")
    print(f"{'='*60}\n")

    # Create case directory
    case_dir.mkdir(exist_ok=True)
    os.chdir(str(case_dir))

    # Set API key if provided
    if COURTLISTENER_API_KEY:
        os.environ['COURTLISTENER_API_KEY'] = COURTLISTENER_API_KEY
        print("✅ CourtListener API key set")

    # ============================================
    # Step 1: Video Ingest
    # ============================================
    print("\n" + "="*60)
    print("📥 Step 1: Video Ingest")
    print("="*60)

    result = subprocess.run(
        f'python3 "{repo_dir}/video_ingest.py" "{YOUTUBE_URL}"',
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(case_dir)
    )

    print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print("⚠️  Errors:", result.stderr)

    # Check if transcript exists
    transcript_file = case_dir / 'transcript.vtt'
    if not transcript_file.exists():
        # Try to find and rename VTT file
        vtt_files = list(case_dir.glob('*.vtt'))
        if vtt_files:
            print(f"\n📝 Found transcript: {vtt_files[0].name}")
            import shutil
            shutil.copy2(vtt_files[0], transcript_file)
            print("✅ Renamed to transcript.vtt")

    # ============================================
    # Step 2: Create cues.json
    # ============================================
    print("\n" + "="*60)
    print("🏷️  Step 2: Creating cues.json")
    print("="*60)

    if transcript_file.exists():
        # Read and parse VTT
        with open(transcript_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse VTT format
        pattern = r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*\n(.*?)(?=\n\n|\Z)'
        matches = re.finditer(pattern, content, re.DOTALL)

        # Keywords for tagging
        court_kw = ['count', 'indictment', 'guilty', 'sentenc', 'conviction', 'verdict',
                    'defendant', 'prosecution', 'judge', 'jury', 'trial', 'testimony',
                    'evidence', 'murder', 'charge', 'attorney']

        foia_kw = ['bodycam', 'dashcam', '911', 'surveillance', 'cctv', 'interrogation',
                   'interview', 'dispatch', 'officer', 'detective', 'investigation']

        cues = []
        for match in matches:
            start_h, start_m, start_s, start_ms = map(int, match.groups()[:4])
            end_h, end_m, end_s, end_ms = map(int, match.groups()[4:8])
            text = match.group(9).strip()

            start = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000
            end = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000

            text = re.sub(r'<[^>]+>', '', text).replace('\n', ' ').strip()

            if text:
                text_lower = text.lower()
                bucket = 'secondary'

                if any(kw in text_lower for kw in court_kw):
                    bucket = 'court'
                elif any(kw in text_lower for kw in foia_kw):
                    bucket = 'foia'

                cues.append({
                    'start': round(start, 2),
                    'end': round(end, 2),
                    'bucket': bucket
                })

        # Merge adjacent segments
        merged = []
        if cues:
            merged.append(cues[0])
            for cue in cues[1:]:
                last = merged[-1]
                if cue['bucket'] == last['bucket'] and cue['start'] - last['end'] <= 5:
                    last['end'] = cue['end']
                else:
                    merged.append(cue)

        # Save
        with open(case_dir / 'cues.json', 'w') as f:
            json.dump(merged, f, indent=2)

        # Stats
        bucket_counts = {}
        for cue in merged:
            duration = cue['end'] - cue['start']
            bucket_counts[cue['bucket']] = bucket_counts.get(cue['bucket'], 0) + duration

        print(f"✅ Created {len(merged)} cues")
        for bucket, duration in sorted(bucket_counts.items()):
            print(f"  {bucket}: {duration:.1f}s")
    else:
        print("⚠️  No transcript found, skipping cues creation")

    # ============================================
    # Step 3: Court Documents
    # ============================================
    print("\n" + "="*60)
    print(f"⚖️  Step 3: Court Documents - {DEFENDANT_NAME}")
    print("="*60)

    result = subprocess.run(
        f'python3 "{repo_dir}/court_docs.py" "{DEFENDANT_NAME}"',
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(case_dir)
    )

    print(result.stdout)

    # ============================================
    # Step 4: FOIA Media
    # ============================================
    print("\n" + "="*60)
    print("🎥 Step 4: FOIA Media")
    print("="*60)

    result = subprocess.run(
        f'python3 "{repo_dir}/foia_media_scraper.py"',
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(case_dir)
    )

    print(result.stdout)

    # ============================================
    # Step 5: News Articles
    # ============================================
    print("\n" + "="*60)
    print("📰 Step 5: News Articles")
    print("="*60)

    for term in NEWS_SEARCH_TERMS:
        print(f"\n🔎 Searching: {term}")
        print("-" * 60)

        result = subprocess.run(
            f'python3 "{repo_dir}/news_scraper.py" "{term}"',
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(case_dir)
        )

        print(result.stdout)

    # ============================================
    # Step 6: Package Bundle
    # ============================================
    print("\n" + "="*60)
    print("📦 Step 6: Creating Bundle")
    print("="*60)

    result = subprocess.run(
        f'python3 "{repo_dir}/packager.py"',
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(case_dir)
    )

    print(result.stdout)

    # ============================================
    # Final Summary
    # ============================================
    print("\n" + "="*60)
    print("✅ PROCESSING COMPLETE!")
    print("="*60)

    bundle_path = case_dir / f"{case_name}_bundle.zip"
    if bundle_path.exists():
        size_mb = bundle_path.stat().st_size / (1024 * 1024)
        print(f"\n📦 Bundle: {bundle_path.name} ({size_mb:.2f} MB)")

        # Count files
        dirs_info = {
            'court_docs': len(list((case_dir / 'court_docs').iterdir())) if (case_dir / 'court_docs').exists() else 0,
            'media': len(list((case_dir / 'media').iterdir())) if (case_dir / 'media').exists() else 0,
            'news': len(list((case_dir / 'news').iterdir())) if (case_dir / 'news').exists() else 0
        }

        print(f"\n📂 Contents:")
        print(f"   Court docs: {dirs_info['court_docs']} files")
        print(f"   FOIA media: {dirs_info['media']} files")
        print(f"   News articles: {dirs_info['news']} files")

        print(f"\n🎯 Case: {DEFENDANT_NAME}")
        print(f"📝 Description: {CASE_DESCRIPTION}")
        print(f"📺 Video: {YOUTUBE_URL}")
        print(f"\n💾 Location: MyDrive/foia_bot/repo/{case_name}/")
    else:
        print("\n⚠️  Bundle not created - check logs above")

    print("\n" + "="*60)
    print("✨ Done! Check Google Drive for your files.")
    print("="*60)

# Run if executed directly
if __name__ == '__main__':
    run_colab_case()
