#!/usr/bin/env python3
"""
Court document fetcher: Searches free sources for court documents
Sources: CourtListener RECAP, GovInfo, DocumentCloud, web PDF search
"""

import json
import re
import sys
import csv
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time


def extract_names_from_transcript(transcript_file):
    """Extract potential defendant names from transcript using 'v.' pattern"""
    if not transcript_file.exists():
        print(f"⚠️  Transcript not found: {transcript_file}")
        return []

    with open(transcript_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Look for patterns like "State of X v. Name" or "People v. Name" or "United States v. Name"
    patterns = [
        r'(?:State\s+of\s+\w+|People|United\s+States|Commonwealth)\s+v\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:trial|case|indictment|arraignment)',
    ]

    names = set()
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            name = match.strip()
            # Filter out common false positives
            if len(name.split()) >= 2 and len(name) > 5:
                names.add(name)

    print(f"🔍 Extracted potential names: {', '.join(names) if names else 'None'}")
    return list(names)


def search_courtlistener(name, output_dir):
    """Search CourtListener RECAP for free court documents"""
    print(f"\n📚 Searching CourtListener for: {name}")

    # CourtListener API (free, no key required for basic search)
    search_url = "https://www.courtlistener.com/api/rest/v3/search/"

    params = {
        'q': f'"{name}"',
        'type': 'r',  # RECAP (dockets)
        'order_by': 'score desc'
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data.get('results', [])
        print(f"  Found {len(results)} results")

        downloaded = []
        for i, result in enumerate(results[:3]):  # Limit to top 3
            # Try to find downloadable PDF link
            # Note: Full document access may require parsing the docket page
            docket_id = result.get('docket_id')
            if docket_id:
                print(f"  Found docket {docket_id}: {result.get('caseName', 'Unknown')}")
                # In a real implementation, you'd fetch the docket page and download PDFs
                # For now, we'll note it in the index

        return downloaded

    except requests.RequestException as e:
        print(f"  ⚠️  CourtListener error: {e}")
        return []


def search_documentcloud(name, output_dir):
    """Search DocumentCloud for public court documents"""
    print(f"\n📄 Searching DocumentCloud for: {name}")

    search_url = "https://api.www.documentcloud.org/api/documents/search/"

    params = {
        'q': f'{name} indictment',
        'per_page': 5
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data.get('results', [])
        print(f"  Found {len(results)} documents")

        downloaded = []
        for doc in results[:3]:
            title = doc.get('title', 'unknown')
            pdf_url = doc.get('canonical_url')

            if pdf_url and pdf_url.endswith('.pdf'):
                # Download the PDF
                filename = f"documentcloud_{doc.get('id', 'unknown')}.pdf"
                filepath = output_dir / filename

                try:
                    pdf_response = requests.get(pdf_url, timeout=30)
                    pdf_response.raise_for_status()

                    with open(filepath, 'wb') as f:
                        f.write(pdf_response.content)

                    print(f"  ✅ Downloaded: {filename}")
                    downloaded.append({
                        'filename': filename,
                        'doc_type': 'documentcloud',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'source': pdf_url
                    })

                    time.sleep(1)  # Be polite

                except requests.RequestException as e:
                    print(f"  ⚠️  Failed to download {filename}: {e}")

        return downloaded

    except requests.RequestException as e:
        print(f"  ⚠️  DocumentCloud error: {e}")
        return []


def search_web_pdfs(name, output_dir):
    """Search for PDFs via DuckDuckGo HTML (no API key needed)"""
    print(f"\n🔎 Searching web for PDF documents: {name}")

    # DuckDuckGo HTML search (free, no API)
    search_url = "https://html.duckduckgo.com/html/"

    query = f'{name} indictment filetype:pdf site:gov'

    try:
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

        # Extract result links
        links = []
        for result in soup.select('.result__a'):
            href = result.get('href')
            if href and 'uddg=' in href:
                # DuckDuckGo wraps URLs
                actual_url = requests.utils.unquote(href.split('uddg=')[1].split('&')[0])
                if actual_url.endswith('.pdf'):
                    links.append(actual_url)

        print(f"  Found {len(links)} PDF links")

        downloaded = []
        for i, url in enumerate(links[:3]):  # Limit to 3
            try:
                filename = f"web_doc_{i+1}.pdf"
                filepath = output_dir / filename

                pdf_response = requests.get(url, timeout=30, headers=headers)
                pdf_response.raise_for_status()

                # Verify it's actually a PDF
                if pdf_response.content[:4] == b'%PDF':
                    with open(filepath, 'wb') as f:
                        f.write(pdf_response.content)

                    print(f"  ✅ Downloaded: {filename}")
                    downloaded.append({
                        'filename': filename,
                        'doc_type': 'web_pdf',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'source': url
                    })

                    time.sleep(2)  # Be polite

            except requests.RequestException as e:
                print(f"  ⚠️  Failed to download {url}: {e}")

        return downloaded

    except requests.RequestException as e:
        print(f"  ⚠️  Web search error: {e}")
        return []


def save_court_index(documents, index_file):
    """Save court document index to CSV"""
    if not documents:
        print("\n⚠️  No documents downloaded")
        return

    with open(index_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'doc_type', 'date', 'source'])
        writer.writeheader()
        writer.writerows(documents)

    print(f"\n✅ Saved {len(documents)} documents to index: {index_file}")


def main():
    working_dir = Path.cwd()
    print(f"📁 Working directory: {working_dir}")

    # Create court_docs subdirectory
    court_docs_dir = working_dir / 'court_docs'
    court_docs_dir.mkdir(exist_ok=True)

    # Load transcript to extract names
    cues_file = working_dir / 'cues.json'
    transcript_file = working_dir / 'transcript.vtt'

    # Try to extract names from transcript
    names = extract_names_from_transcript(transcript_file)

    if not names:
        print("\n⚠️  No names found in transcript. You can manually specify names as arguments.")
        if len(sys.argv) > 1:
            names = [' '.join(sys.argv[1:])]
        else:
            print("Usage: python court_docs.py [optional: \"Name to search\"]")
            sys.exit(1)

    all_documents = []

    for name in names[:2]:  # Limit to 2 names to avoid excessive searches
        print(f"\n{'='*60}")
        print(f"Searching for: {name}")
        print('='*60)

        # Try each source
        docs = search_courtlistener(name, court_docs_dir)
        all_documents.extend(docs)

        docs = search_documentcloud(name, court_docs_dir)
        all_documents.extend(docs)

        docs = search_web_pdfs(name, court_docs_dir)
        all_documents.extend(docs)

        time.sleep(2)  # Rate limiting between names

    # Save index
    index_file = working_dir / 'court_index.csv'
    save_court_index(all_documents, index_file)

    print("\n✅ Court document search complete!")


if __name__ == '__main__':
    main()
