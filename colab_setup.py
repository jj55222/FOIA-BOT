#!/usr/bin/env python3
"""
Google Colab Setup Script for FOIA-BOT
Run this first in a Colab notebook to set up the environment
"""

import os
import sys
from pathlib import Path

def setup_colab():
    """Set up FOIA-BOT in Google Colab environment"""

    print("🚀 FOIA-BOT Colab Setup")
    print("=" * 60)

    # Check if running in Colab
    try:
        import google.colab
        IN_COLAB = True
        print("✓ Running in Google Colab")
    except ImportError:
        IN_COLAB = False
        print("⚠️  Not running in Colab - setup may not work correctly")

    # Mount Google Drive
    if IN_COLAB:
        print("\n📁 Mounting Google Drive...")
        try:
            from google.colab import drive
            drive.mount('/content/drive', force_remount=False)
            print("✓ Google Drive mounted")
        except Exception as e:
            print(f"❌ Failed to mount Drive: {e}")
            return False

    # Set up working directory
    base_dir = Path('/content/drive/MyDrive/foia_bot')
    repo_dir = base_dir / 'repo'

    print(f"\n📂 Setting up directories...")
    print(f"   Base: {base_dir}")
    print(f"   Repo: {repo_dir}")

    # Create directories
    base_dir.mkdir(parents=True, exist_ok=True)
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Change to repo directory
    os.chdir(str(repo_dir))
    print(f"✓ Working directory: {os.getcwd()}")

    # Install/upgrade dependencies
    print("\n📦 Installing dependencies...")
    dependencies = [
        'yt-dlp>=2023.12.30',
        'requests>=2.31.0',
        'beautifulsoup4>=4.12.0',
        'feedparser>=6.0.10',
        'newspaper3k>=0.2.8',
        'lxml_html_clean>=0.1.0',
        'pandas>=2.1.0',
        'matplotlib>=3.8.0',
    ]

    import subprocess
    for dep in dependencies:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', dep],
                         check=True, capture_output=True)
            print(f"✓ {dep.split('>=')[0]}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to install {dep}: {e}")

    # Check if FOIA-BOT scripts exist
    required_scripts = [
        'video_ingest.py',
        'court_docs.py',
        'foia_media_scraper.py',
        'news_scraper.py',
        'packager.py',
        'process_case.sh'
    ]

    print("\n🔍 Checking for FOIA-BOT scripts...")
    missing_scripts = []
    for script in required_scripts:
        script_path = repo_dir / script
        if script_path.exists():
            print(f"✓ {script}")
        else:
            print(f"❌ {script} - NOT FOUND")
            missing_scripts.append(script)

    if missing_scripts:
        print("\n⚠️  Missing scripts detected!")
        print("   Please copy the FOIA-BOT files to:")
        print(f"   {repo_dir}")
        print("\n   Or clone the repo:")
        print("   !git clone https://github.com/jj55222/FOIA-BOT.git /content/drive/MyDrive/foia_bot/repo")
        return False

    # Make bash script executable
    bash_script = repo_dir / 'process_case.sh'
    if bash_script.exists():
        bash_script.chmod(0o755)
        print(f"\n✓ Made process_case.sh executable")

    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("   1. Run process_case() with your YouTube URL")
    print("   2. Or use individual functions for each step")
    print("\nExample:")
    print('   process_case("https://www.youtube.com/watch?v=VIDEO_ID", "case_name")')

    return True


def process_case(youtube_url, case_name=None):
    """
    Process a FOIA-BOT case in Colab

    Args:
        youtube_url: YouTube URL to process
        case_name: Optional custom case name (default: auto-generated from video ID)
    """
    import subprocess
    import re
    from datetime import datetime

    # Generate case name if not provided
    if not case_name:
        match = re.search(r'v=([a-zA-Z0-9_-]+)', youtube_url)
        if match:
            case_name = match.group(1)
        else:
            case_name = f"case_{int(datetime.now().timestamp())}"

    case_dir = f"case_{datetime.now().strftime('%Y%m%d')}_{case_name}"

    print(f"🎬 Processing: {youtube_url}")
    print(f"📁 Case directory: {case_dir}")
    print("=" * 60)

    # Get script directory (where this script is located)
    script_dir = Path(__file__).parent.absolute() if '__file__' in globals() else Path.cwd()

    # Create case directory
    case_path = Path(case_dir)
    case_path.mkdir(exist_ok=True)
    os.chdir(str(case_path))

    print(f"Working in: {os.getcwd()}\n")

    # Run each step
    steps = [
        ("Video Ingest", f'python3 "{script_dir}/video_ingest.py" "{youtube_url}"'),
        ("Court Documents", f'python3 "{script_dir}/court_docs.py"'),
        ("FOIA Media", f'python3 "{script_dir}/foia_media_scraper.py"'),
        ("News Scraping", f'python3 "{script_dir}/news_scraper.py"'),
        ("Packaging", f'python3 "{script_dir}/packager.py"'),
    ]

    for i, (step_name, command) in enumerate(steps, 1):
        print(f"\n[{i}/5] {step_name}")
        print("─" * 60)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=False,  # Show output directly
                text=True
            )
            if result.returncode == 0:
                print(f"✓ {step_name} completed")
            else:
                print(f"⚠️  {step_name} failed (continuing anyway)")
        except Exception as e:
            print(f"❌ Error in {step_name}: {e}")
            print("Continuing to next step...")

    print("\n" + "=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)
    print(f"\n📦 Bundle location: {case_path.absolute()}/{case_dir}_bundle.zip")


if __name__ == '__main__':
    # Run setup when script is executed
    setup_colab()
