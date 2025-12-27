#!/usr/bin/env python3
"""
FOIA media scraper: Searches for publicly available FOIA-type media
Looks for bodycam, dashcam, 911 audio, surveillance footage, etc.
"""

import json
import re
import sys
import csv
from pathlib import Path
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import time


def load_foia_cues(cues_file):
    """Load cues.json and extract FOIA-bucket segments"""
    if not cues_file.exists():
        print(f"⚠️  Cues file not found: {cues_file}")
        return []

    with open(cues_file, 'r') as f:
        cues = json.load(f)

    # Filter for FOIA bucket
    foia_cues = [c for c in cues if c.get('bucket') == 'foia']

    print(f"🔍 Found {len(foia_cues)} FOIA-tagged segments")
    return foia_cues


def extract_keywords_from_transcript(transcript_file, foia_cues):
    """Extract relevant keywords from FOIA segments in transcript"""
    if not transcript_file.exists():
        return []

    with open(transcript_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple keyword extraction - look for FOIA-related terms
    keywords = set()

    foia_terms = [
        'bodycam', 'body-cam', 'body cam',
        'dashcam', 'dash-cam', 'dash cam',
        '911', 'dispatch',
        'surveillance', 'cctv',
        'interrogation', 'interview',
        'police footage', 'officer'
    ]

    content_lower = content.lower()
    for term in foia_terms:
        if term in content_lower:
            keywords.add(term)

    # Also try to extract location/city names
    # Simple pattern: capitalized words
    cities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', content)
    # Filter to likely city names (this is very basic)
    for city in cities[:5]:  # Limit
        if len(city.split()) <= 2:
            keywords.add(city)

    print(f"📝 Extracted keywords: {', '.join(keywords)}")
    return list(keywords)


def search_duckduckgo_videos(keywords, max_results=5):
    """Search DuckDuckGo for video files"""
    print(f"\n🔎 Searching for video files with keywords: {keywords[:3]}")

    video_urls = []

    for keyword in keywords[:3]:  # Limit searches
        query = f'{keyword} police video mp4'

        try:
            search_url = "https://html.duckduckgo.com/html/"
            data = {
                'q': query,
                'kl': 'us-en'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.post(search_url, data=data, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract links
            for result in soup.select('.result__a')[:5]:
                href = result.get('href')
                if href and 'uddg=' in href:
                    actual_url = requests.utils.unquote(href.split('uddg=')[1].split('&')[0])

                    # Check if it's a direct video file
                    if any(actual_url.lower().endswith(ext) for ext in ['.mp4', '.mov', '.m4v', '.avi']):
                        video_urls.append(actual_url)
                        print(f"  Found: {actual_url}")

            time.sleep(2)  # Rate limiting

        except requests.RequestException as e:
            print(f"  ⚠️  Search error: {e}")

    return video_urls


def try_predictable_pd_urls(keywords):
    """Try predictable police department video hosting patterns"""
    print(f"\n🏛️  Checking predictable PD video URLs...")

    potential_urls = []

    # Extract potential city names from keywords
    cities = [kw for kw in keywords if kw[0].isupper() and ' ' not in kw]

    common_patterns = [
        'https://www.{city}police.gov/videos/',
        'https://www.{city}police.gov/wp-content/uploads/',
        'https://{city}pd.gov/media/',
        'https://www.ci.{city}.us/police/videos/',
    ]

    for city in cities[:2]:  # Limit
        city_lower = city.lower().replace(' ', '')

        for pattern in common_patterns:
            url = pattern.format(city=city_lower)
            potential_urls.append(url)

    # Try to access these URLs
    found_urls = []
    for url in potential_urls[:10]:  # Limit attempts
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                print(f"  ✅ Found accessible URL: {url}")
                found_urls.append(url)
            time.sleep(1)
        except requests.RequestException:
            pass  # URL doesn't exist or isn't accessible

    return found_urls


def download_media_file(url, output_dir, index):
    """Download a media file"""
    try:
        # Get file extension from URL
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix or '.mp4'

        filename = f"foia_media_{index}{ext}"
        filepath = output_dir / filename

        print(f"  📥 Downloading: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        # Download in chunks
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = filepath.stat().st_size
        print(f"  ✅ Downloaded: {filename} ({file_size / 1024 / 1024:.1f} MB)")

        return {
            'filename': filename,
            'source_url': url,
            'size_mb': round(file_size / 1024 / 1024, 2)
        }

    except requests.RequestException as e:
        print(f"  ⚠️  Download failed: {e}")
        return None


def save_media_index(media_files, index_file):
    """Save media index to CSV"""
    if not media_files:
        print("\n⚠️  No media files downloaded")
        return

    with open(index_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'source_url', 'size_mb'])
        writer.writeheader()
        writer.writerows(media_files)

    print(f"\n✅ Saved {len(media_files)} media files to index: {index_file}")


def main():
    working_dir = Path.cwd()
    print(f"📁 Working directory: {working_dir}")

    # Create media subdirectory
    media_dir = working_dir / 'media'
    media_dir.mkdir(exist_ok=True)

    # Load cues to find FOIA segments
    cues_file = working_dir / 'cues.json'
    foia_cues = load_foia_cues(cues_file)

    # Extract keywords from transcript
    transcript_file = working_dir / 'transcript.vtt'
    keywords = extract_keywords_from_transcript(transcript_file, foia_cues)

    if not keywords:
        print("\n⚠️  No FOIA keywords found. Using default search terms.")
        keywords = ['bodycam', 'police video']

    # Search for videos
    video_urls = search_duckduckgo_videos(keywords)

    # Try predictable PD URLs
    pd_urls = try_predictable_pd_urls(keywords)

    # Combine all found URLs
    all_urls = list(set(video_urls + pd_urls))

    print(f"\n📊 Found {len(all_urls)} potential media URLs")

    # Download media files
    downloaded_files = []
    for i, url in enumerate(all_urls[:5], 1):  # Limit to 5 downloads
        result = download_media_file(url, media_dir, i)
        if result:
            downloaded_files.append(result)
        time.sleep(2)  # Be polite

    # Save index
    index_file = working_dir / 'media_index.csv'
    save_media_index(downloaded_files, index_file)

    print("\n✅ FOIA media scraping complete!")
    print(f"   Downloaded {len(downloaded_files)} files")


if __name__ == '__main__':
    main()
