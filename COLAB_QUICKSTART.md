# Google Colab Quick Start Guide

## 🚀 Fastest Way to Run FOIA-BOT in Colab

### Method 1: Copy-Paste This Into a New Colab Notebook

```python
# ============================================
# FOIA-BOT Quick Start for Google Colab
# ============================================

# 1. Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# 2. Install dependencies
print("📦 Installing dependencies...")
!pip install -q yt-dlp requests beautifulsoup4 feedparser newspaper3k lxml_html_clean pandas matplotlib

# 3. Clone repo directly to Google Drive
import os
from pathlib import Path

repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')

if not (repo_dir / 'video_ingest.py').exists():
    print("\n📥 Cloning FOIA-BOT...")
    !git clone https://github.com/jj55222/FOIA-BOT.git {str(repo_dir)}
    print("✅ Cloned successfully!")
else:
    print("\n✅ FOIA-BOT already installed")

print(f"\n📁 Repository location: {repo_dir}")

# 4. Change to repo directory
os.chdir(str(repo_dir))

# 5. Configure your case
YOUTUBE_URL = "https://www.youtube.com/watch?v=UQt46gvYO40"  # ← CHANGE THIS
CASE_NAME = "test_case"  # ← CHANGE THIS

# 6. Create case directory
import re
from datetime import datetime

match = re.search(r'v=([a-zA-Z0-9_-]+)', YOUTUBE_URL)
slug = CASE_NAME if CASE_NAME else (match.group(1) if match else f"case_{int(datetime.now().timestamp())}")
case_dir = f"case_{datetime.now().strftime('%Y%m%d')}_{slug}"

case_path = repo_dir / case_dir
case_path.mkdir(exist_ok=True)
os.chdir(str(case_path))

print(f"\n🎬 Processing: {YOUTUBE_URL}")
print(f"📁 Case directory: {case_path}")

# 7. Run the pipeline
import subprocess

steps = [
    ("Video Ingest", f'python3 {repo_dir}/video_ingest.py "{YOUTUBE_URL}"'),
    ("Court Documents", f'python3 {repo_dir}/court_docs.py'),
    ("FOIA Media", f'python3 {repo_dir}/foia_media_scraper.py'),
    ("News Scraping", f'python3 {repo_dir}/news_scraper.py'),
    ("Packaging", f'python3 {repo_dir}/packager.py'),
]

for i, (step_name, command) in enumerate(steps, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/5] {step_name}")
    print('='*60)

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr and result.returncode != 0:
        print("⚠️  STDERR:", result.stderr)

    print(f"{'✓' if result.returncode == 0 else '⚠️ '} {step_name} {'completed' if result.returncode == 0 else 'failed (continuing)'}")

print(f"\n{'='*60}")
print("✅ DONE!")
print(f"{'='*60}")
print(f"\n📦 Your bundle: {case_path}/{case_dir}_bundle.zip")
print(f"\n💾 Download from Google Drive:")
print(f"   MyDrive/foia_bot/repo/{case_dir}/")
```

---

## Method 2: Step-by-Step (For Testing Each Part)

### Step 1: Setup (Run Once)

```python
from google.colab import drive
drive.mount('/content/drive')

!pip install -q yt-dlp requests beautifulsoup4 feedparser newspaper3k lxml_html_clean pandas matplotlib

from pathlib import Path
import os

repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')
if not (repo_dir / 'video_ingest.py').exists():
    !git clone https://github.com/jj55222/FOIA-BOT.git {str(repo_dir)}

os.chdir(str(repo_dir))
print(f"✅ Ready! Working in: {os.getcwd()}")
```

### Step 2: Create Case Directory

```python
import os
from pathlib import Path
from datetime import datetime

repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')
case_dir = f"case_{datetime.now().strftime('%Y%m%d')}_test"
case_path = repo_dir / case_dir
case_path.mkdir(exist_ok=True)
os.chdir(str(case_path))

print(f"📁 Case directory: {case_path}")
```

### Step 3: Run Video Ingest

```python
YOUTUBE_URL = "https://www.youtube.com/watch?v=UQt46gvYO40"  # Change this!
repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')

!python3 {str(repo_dir)}/video_ingest.py "{YOUTUBE_URL}"
```

### Step 4: Run Other Steps (Optional)

```python
repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')

!python3 {str(repo_dir)}/court_docs.py
!python3 {str(repo_dir)}/foia_media_scraper.py
!python3 {str(repo_dir)}/news_scraper.py
!python3 {str(repo_dir)}/packager.py
```

### Step 5: Download Bundle

```python
from google.colab import files
import glob

bundles = sorted(glob.glob('/content/drive/MyDrive/foia_bot/repo/case_*/*_bundle.zip'))
if bundles:
    files.download(bundles[-1])
```

---

## 🐛 Troubleshooting

### Error: "No such file or directory"

**Problem**: Scripts can't be found

**Solution**: Make sure you're cloning directly to Drive (not `/tmp/`):
```python
repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')
!git clone https://github.com/jj55222/FOIA-BOT.git {str(repo_dir)}
```

### Error: "getcwd: cannot access parent directories"

**Problem**: Directory was deleted or doesn't exist

**Solution**: Always use absolute paths and verify directory exists:
```python
import os
from pathlib import Path

repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')
case_dir = repo_dir / 'case_20251228_test'
case_dir.mkdir(exist_ok=True)
os.chdir(str(case_dir))
```

### Error: yt-dlp download failed

**Problem**: Video might be private, age-restricted, or network issue

**Solution**:
- Try a different video
- Check the detailed error output (now shown)
- Update yt-dlp: `!pip install -U yt-dlp`

---

## 📌 Important Notes

1. **Always mount Drive first**: `drive.mount('/content/drive')`
2. **Use `/content/drive/` not `/tmp/`**: More reliable in Colab
3. **Use absolute paths**: Prevents directory errors
4. **Check files exist**: Verify after cloning
5. **Create case directories**: Don't run scripts in repo root

---

## 💡 Pro Tips

- **Keep cases in Drive**: They persist between sessions
- **Use the notebook**: `FOIA_BOT_Colab.ipynb` for easiest experience
- **Check Drive quota**: Videos can be large (500MB-2GB per case)
- **Download bundles**: Free up Drive space by downloading and deleting old cases
