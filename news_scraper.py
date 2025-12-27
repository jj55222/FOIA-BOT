#!/usr/bin/env python3
"""
News scraper: Fetches news articles from Google News RSS
Uses feedparser and newspaper3k for free article extraction
"""

import sys
import csv
import re
from pathlib import Path
from datetime import datetime
import feedparser
from newspaper import Article
import time


def extract_search_terms(transcript_file):
    """Extract search terms from transcript (names, locations)"""
    if not transcript_file.exists():
        print(f"⚠️  Transcript not found: {transcript_file}")
        return []

    with open(transcript_file, 'r', encoding='utf-8') as f:
        content = f.read()

    search_terms = []

    # Look for names in "v." patterns
    name_pattern = r'(?:State\s+of\s+\w+|People|United\s+States)\s+v\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
    names = re.findall(name_pattern, content, re.IGNORECASE)

    for name in names[:2]:  # Limit to 2 names
        search_terms.append(name.strip())

    # If no names found, look for any capitalized multi-word phrases
    if not search_terms:
        phrases = re.findall(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', content)
        search_terms = list(set(phrases))[:2]

    print(f"🔍 Search terms: {', '.join(search_terms) if search_terms else 'None'}")
    return search_terms


def fetch_google_news_rss(search_term, max_results=20):
    """Fetch news articles from Google News RSS feed"""
    print(f"\n📰 Fetching news for: {search_term}")

    # Google News RSS search URL
    search_query = f"{search_term} murder"  # Add 'murder' context for crime cases
    rss_url = f"https://news.google.com/rss/search?q={search_query.replace(' ', '%20')}"

    try:
        feed = feedparser.parse(rss_url)

        if feed.bozo:  # feedparser sets this flag if there's an error
            print(f"  ⚠️  RSS feed error")
            return []

        entries = feed.entries[:max_results]
        print(f"  Found {len(entries)} news items")

        articles = []
        for entry in entries:
            articles.append({
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'source': entry.get('source', {}).get('title', 'Unknown')
            })

        return articles

    except Exception as e:
        print(f"  ⚠️  Error fetching RSS: {e}")
        return []


def download_article(url, output_dir, index):
    """Download and parse article using newspaper3k"""
    try:
        print(f"  📥 Downloading article {index}: {url[:60]}...")

        article = Article(url)
        article.download()
        article.parse()

        # Save article text
        filename = f"article_{index}.txt"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Title: {article.title}\n")
            f.write(f"Authors: {', '.join(article.authors)}\n")
            f.write(f"Published: {article.publish_date}\n")
            f.write(f"URL: {url}\n")
            f.write(f"\n{'='*60}\n\n")
            f.write(article.text)

        print(f"  ✅ Saved: {filename}")

        return {
            'filename': filename,
            'title': article.title,
            'url': url,
            'date': str(article.publish_date) if article.publish_date else 'Unknown',
            'word_count': len(article.text.split())
        }

    except Exception as e:
        print(f"  ⚠️  Failed to download article: {e}")
        return None


def save_news_index(articles, index_file):
    """Save news index to CSV"""
    if not articles:
        print("\n⚠️  No articles downloaded")
        return

    with open(index_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['filename', 'title', 'url', 'date', 'word_count'])
        writer.writeheader()
        writer.writerows(articles)

    print(f"\n✅ Saved {len(articles)} articles to index: {index_file}")


def generate_summary(news_dir):
    """Generate a simple summary of headlines"""
    summary_file = news_dir.parent / 'news_summary.txt'

    articles = list(news_dir.glob('article_*.txt'))

    if not articles:
        return

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("NEWS SUMMARY\n")
        f.write("=" * 60 + "\n\n")

        for article_file in sorted(articles):
            with open(article_file, 'r', encoding='utf-8') as af:
                lines = af.readlines()
                title = lines[0].replace('Title: ', '').strip() if lines else 'Unknown'
                f.write(f"• {title}\n")

        f.write(f"\n\nTotal articles: {len(articles)}\n")

    print(f"📝 Generated summary: news_summary.txt")


def main():
    working_dir = Path.cwd()
    print(f"📁 Working directory: {working_dir}")

    # Create news subdirectory
    news_dir = working_dir / 'news'
    news_dir.mkdir(exist_ok=True)

    # Extract search terms from transcript
    transcript_file = working_dir / 'transcript.vtt'
    search_terms = extract_search_terms(transcript_file)

    if not search_terms:
        print("\n⚠️  No search terms found. You can manually specify as arguments.")
        if len(sys.argv) > 1:
            search_terms = [' '.join(sys.argv[1:])]
        else:
            print("Usage: python news_scraper.py [optional: \"Search term\"]")
            sys.exit(1)

    # Fetch news for each search term
    all_news = []
    for term in search_terms[:2]:  # Limit to 2 search terms
        news_items = fetch_google_news_rss(term)
        all_news.extend(news_items)

    print(f"\n📊 Total news items found: {len(all_news)}")

    # Download articles
    downloaded_articles = []
    for i, news_item in enumerate(all_news[:20], 1):  # Limit to top 20
        result = download_article(news_item['link'], news_dir, i)
        if result:
            downloaded_articles.append(result)
        time.sleep(1)  # Be polite to news sites

    # Save index
    index_file = working_dir / 'news_index.csv'
    save_news_index(downloaded_articles, index_file)

    # Generate summary
    generate_summary(news_dir)

    print("\n✅ News scraping complete!")
    print(f"   Downloaded {len(downloaded_articles)} articles")


if __name__ == '__main__':
    main()
