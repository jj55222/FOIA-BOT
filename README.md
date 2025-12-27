# FOIA-BOT

**Free, zero-cost video case bundler for investigative journalism and true crime research**

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

### 2. Process a Case

```bash
./process_case.sh "https://www.youtube.com/watch?v=VIDEO_ID" my_case_name
```

That's it! The script will:
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
