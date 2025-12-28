# FOIA-BOT

**Free, zero-cost video case bundler for investigative journalism and true crime research**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jj55222/FOIA-BOT/blob/main/FOIA_BOT_Colab.ipynb)

FOIA-BOT automatically processes YouTube videos about criminal cases and creates comprehensive research bundles by:
- Downloading videos and extracting captions
- Categorizing content (court proceedings, FOIA materials, news)
- Scraping related court documents from free sources
- Finding publicly available FOIA-type media (bodycam, 911, etc.)
- Collecting news articles
- Packaging everything into a shareable bundle

## ✨ Key Features

- **100% Free**: Uses only free APIs and services - no paid subscriptions needed
- **Zero Cloud Costs**: All data stored locally in organized case folders
- **Automated Pipeline**: One command processes everything
- **Smart Categorization**: AI-powered bucket tagging (court/FOIA/secondary)
- **Multi-Source**: Pulls from CourtListener, DocumentCloud, Google News, and more
- **Self-Contained**: Each case is a complete standalone bundle

## 📋 Requirements

- Python 3.8+
- yt-dlp (for video download)
- Internet connection
- ~500MB-2GB free disk space per case

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/yourusername/FOIA-BOT.git
cd FOIA-BOT

# Install Python dependencies
pip install -r requirements.txt

# Install yt-dlp (if not already installed)
pip install yt-dlp
```

### 2a. Process a Case (Local/Terminal)

```bash
./process_case.sh "https://www.youtube.com/watch?v=VIDEO_ID" my_case_name
```

### 2b. Process a Case (Google Colab)

**📖 See [COLAB_QUICKSTART.md](COLAB_QUICKSTART.md) for detailed Colab instructions**

**Quick Method (Copy-Paste into Colab):**

```python
# 1. Mount Drive & Install
from google.colab import drive
drive.mount('/content/drive')
!pip install -q yt-dlp requests beautifulsoup4 feedparser newspaper3k lxml_html_clean pandas matplotlib

# 2. Clone repo (first time only)
from pathlib import Path
repo_dir = Path('/content/drive/MyDrive/foia_bot/repo')
if not (repo_dir / 'video_ingest.py').exists():
    !git clone https://github.com/jj55222/FOIA-BOT.git {str(repo_dir)}

# 3. Run pipeline
import os
os.chdir(str(repo_dir))
!mkdir -p test_case && cd test_case
!python3 {str(repo_dir)}/video_ingest.py "YOUR_YOUTUBE_URL"
!python3 {str(repo_dir)}/court_docs.py
!python3 {str(repo_dir)}/foia_media_scraper.py
!python3 {str(repo_dir)}/news_scraper.py
!python3 {str(repo_dir)}/packager.py
```

**Or use the interactive notebook:** Open `FOIA_BOT_Colab.ipynb` in Google Colab

**That's it! The script will:**
1. Download the video and captions
2. Tag content by type (court/FOIA/secondary)
3. Search for court documents
4. Scrape for FOIA media
5. Collect news articles
6. Create a zip bundle

### 3. Review the Output

```
case_20231215_my_case_name/
├── raw_video.mp4              # Original video
├── transcript.vtt             # Video captions
├── cues.json                  # Timestamped content buckets
├── composition_chart.png      # Visual breakdown
├── README.md                  # Case summary
├── court_docs/                # Court documents
│   └── *.pdf
├── media/                     # FOIA-type media files
│   └── *.mp4
├── news/                      # News articles
│   └── article_*.txt
└── case_20231215_my_case_name_bundle.zip  # Complete bundle
```

## 🛠️ Manual Usage

You can also run individual components:

```bash
# Create case directory
mkdir case_20231215_mycase
cd case_20231215_mycase

# Step 1: Download and tag video
python ../video_ingest.py "https://youtube.com/watch?v=..."

# Step 2: Find court documents
python ../court_docs.py

# Step 3: Scrape FOIA media
python ../foia_media_scraper.py

# Step 4: Collect news articles
python ../news_scraper.py

# Step 5: Create bundle
python ../packager.py
```

## 📊 How It Works

### 1. Video Ingest (`video_ingest.py`)

- Downloads video using **yt-dlp**
- Extracts YouTube auto-generated captions (free)
- Falls back to local Whisper if no captions available
- Tags segments using keyword heuristics:
  - **Court**: indictment, guilty, trial, testimony, etc.
  - **FOIA**: bodycam, 911 audio, dashcam, surveillance, etc.
  - **Secondary**: everything else
- Outputs `cues.json` with timestamped buckets

### 2. Court Document Search (`court_docs.py`)

Searches multiple **free** sources:
- **CourtListener RECAP**: Mirror of PACER filings (no fees)
- **DocumentCloud**: Public document database
- **GovInfo.gov**: Federal opinions and indictments
- **Web search**: Google/DuckDuckGo for `.gov` PDFs

Saves PDFs to `court_docs/` and creates `court_index.csv`

### 3. FOIA Media Scraper (`foia_media_scraper.py`)

- Extracts keywords from FOIA-tagged segments
- Searches for direct video links (`.mp4`, `.mov`)
- Checks predictable police department URLs
- Downloads public bodycam/dashcam footage
- Saves to `media/` with `media_index.csv`

### 4. News Scraper (`news_scraper.py`)

- Queries Google News RSS (free, no API key)
- Parses articles with `newspaper3k`
- Extracts full text and metadata
- Saves to `news/` with `news_index.csv`

### 5. Packager (`packager.py`)

- Analyzes all collected data
- Creates composition chart with `matplotlib`
- Generates comprehensive README
- Zips entire case folder for distribution

## 🔧 Configuration

### Custom Search Terms

Manually specify names or keywords:

```bash
python court_docs.py "John Doe"
python news_scraper.py "Criminal Case 2023"
```

### Adjust Bucket Keywords

Edit the keyword lists in `video_ingest.py`:

```python
court_keywords = [
    'count i', 'indictment', 'guilty', 'sentenc', ...
]

foia_keywords = [
    'bodycam', 'dashcam', '911 audio', ...
]
```

## 💡 Use Cases

- **True crime research**: Bundle all materials for a case
- **Investigative journalism**: Compile sources for reporting
- **Legal research**: Organize case materials
- **Documentary production**: Gather background materials
- **Academic research**: Create annotated case studies

## 🌟 What Makes This Free?

| Need | Free Solution |
|------|---------------|
| Video download | yt-dlp |
| Captions | YouTube auto-generated |
| Speech-to-text | whisper.cpp (local, optional) |
| Court docs | CourtListener RECAP, GovInfo |
| News search | Google News RSS (no API key) |
| Media scraping | Direct web search |
| Storage | Local filesystem |
| Visualization | matplotlib |

**No API keys. No subscriptions. No cloud bills.**

## 📝 Directory Convention

Each case follows this structure:

```
case_YYYYMMDD_<slug>/
├── raw_video.mp4
├── transcript.vtt
├── cues.json
├── court_docs/
├── media/
├── news/
└── package/
```

Agents read & write inside the case folder to avoid external storage costs.

## 🐛 Troubleshooting

### Common Issues

#### yt-dlp Download Failures

If video download fails, you'll now see the detailed error output. Common causes:

- **Video is private or age-restricted**: Some videos require authentication
- **Network issues**: Check your internet connection
- **Outdated yt-dlp**: Update with `pip install -U yt-dlp`
- **Rate limiting**: YouTube may temporarily block requests

**Solution**: Try a different video or wait a few minutes before retrying.

#### newspaper3k ImportError

```
ImportError: lxml.html.clean module is now a separate project lxml_html_clean.
```

**Solution**: This is fixed in requirements.txt. Ensure you've installed all dependencies:

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install lxml_html_clean
```

#### No Captions Available

If YouTube doesn't provide auto-captions, you can:

1. Use a video with English captions
2. Enable local Whisper fallback (see code comments in `video_ingest.py`)
3. Manually provide a transcript in VTT format

#### Empty or Missing Results

If scraping returns no results:

- **Court docs**: Case may not have public records yet, or names weren't detected
- **FOIA media**: Not all cases have publicly released media
- **News articles**: Try providing specific search terms manually

The pipeline continues even if some steps fail, so you'll still get a bundle with available data.

#### Google Colab "No such file or directory"

If you get errors like `bash: process_case.sh: No such file or directory`:

1. **Mount Google Drive first**:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```

2. **Use the Colab notebook** (`FOIA_BOT_Colab.ipynb`) instead of bash commands

3. **Or navigate to the repo directory**:
   ```python
   %cd /content/drive/MyDrive/foia_bot/repo
   ```

4. **Don't use bash scripts** - Use the Python functions from `colab_setup.py` instead

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Additional court document sources
- Better name/entity extraction
- OCR for video analysis
- Enhanced keyword detection
- More FOIA source patterns

## ⚖️ Legal & Ethics

- **Respect robots.txt** and rate limits
- **Public data only** - no credential stuffing or unauthorized access
- **Fair use** - for research, journalism, and education
- **Verify sources** - cross-check document authenticity
- **Privacy** - redact PII when sharing bundles

## 📜 License

MIT License - see LICENSE file

## 🙏 Acknowledgments

Built with:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Video download
- [CourtListener](https://www.courtlistener.com/) - Free legal documents
- [DocumentCloud](https://www.documentcloud.org/) - Public document access
- [newspaper3k](https://github.com/codelucas/newspaper) - Article extraction
- [feedparser](https://github.com/kurtmckee/feedparser) - RSS parsing

## 📧 Contact

For questions, issues, or suggestions, please open a GitHub issue.

---

**Disclaimer**: This tool is for research and educational purposes. Always verify information independently and respect intellectual property rights.
