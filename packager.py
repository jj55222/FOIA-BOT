#!/usr/bin/env python3
"""
Packager: Creates final bundle with visualization and README
Reads all index files, generates statistics, and creates a zip archive
"""

import json
import csv
import sys
from pathlib import Path
from datetime import datetime
import zipfile
import matplotlib.pyplot as plt
import matplotlib


# Use non-interactive backend
matplotlib.use('Agg')


def analyze_cues(cues_file):
    """Analyze cues.json to get bucket statistics"""
    if not cues_file.exists():
        print(f"⚠️  Cues file not found: {cues_file}")
        return {}

    with open(cues_file, 'r') as f:
        cues = json.load(f)

    bucket_stats = {}
    total_duration = 0

    for cue in cues:
        bucket = cue.get('bucket', 'unknown')
        duration = cue['end'] - cue['start']

        bucket_stats[bucket] = bucket_stats.get(bucket, 0) + duration
        total_duration += duration

    # Calculate percentages
    bucket_percentages = {}
    for bucket, duration in bucket_stats.items():
        percentage = (duration / total_duration * 100) if total_duration > 0 else 0
        bucket_percentages[bucket] = {
            'duration': round(duration, 2),
            'percentage': round(percentage, 1)
        }

    print(f"\n📊 Bucket analysis:")
    for bucket, stats in sorted(bucket_percentages.items()):
        print(f"  {bucket}: {stats['duration']}s ({stats['percentage']}%)")

    return bucket_percentages


def create_visualization(bucket_stats, output_file):
    """Create a bar chart of bucket composition"""
    if not bucket_stats:
        print("⚠️  No bucket data to visualize")
        return

    print(f"\n📈 Creating visualization...")

    buckets = list(bucket_stats.keys())
    percentages = [stats['percentage'] for stats in bucket_stats.values()]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bar chart
    colors = {'court': '#3498db', 'foia': '#e74c3c', 'secondary': '#95a5a6'}
    bar_colors = [colors.get(b, '#7f8c8d') for b in buckets]

    bars = ax.bar(buckets, percentages, color=bar_colors)

    # Customize chart
    ax.set_ylabel('Percentage (%)', fontsize=12)
    ax.set_xlabel('Content Type', fontsize=12)
    ax.set_title('Video Content Composition', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)

    # Add percentage labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"  ✅ Saved chart: {output_file.name}")


def read_csv_index(csv_file):
    """Read a CSV index file"""
    if not csv_file.exists():
        return []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def generate_readme(working_dir, bucket_stats):
    """Generate comprehensive README.md"""
    print(f"\n📝 Generating README...")

    slug = working_dir.name
    readme_file = working_dir / 'README.md'

    # Load indices
    court_index = read_csv_index(working_dir / 'court_index.csv')
    media_index = read_csv_index(working_dir / 'media_index.csv')
    news_index = read_csv_index(working_dir / 'news_index.csv')

    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(f"# Case Bundle: {slug}\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Runtime composition
        f.write("## Runtime Composition\n\n")
        if bucket_stats:
            for bucket, stats in sorted(bucket_stats.items()):
                f.write(f"- **{bucket.capitalize()}**: {stats['percentage']}% "
                       f"({stats['duration']}s)\n")
        else:
            f.write("*No bucket data available*\n")

        f.write("\n![Content Composition](composition_chart.png)\n\n")

        # Files section
        f.write("## Files\n\n")

        # Video and transcript
        f.write("### Source Video\n\n")
        video_files = list(working_dir.glob('raw_video.*'))
        if video_files:
            for vf in video_files:
                size_mb = vf.stat().st_size / 1024 / 1024
                f.write(f"- `{vf.name}` ({size_mb:.1f} MB)\n")
        f.write(f"- `transcript.vtt` - Video captions\n")
        f.write(f"- `cues.json` - Timestamp buckets\n\n")

        # Court documents
        f.write("### Court Documents\n\n")
        if court_index:
            f.write("| Filename | Doc Type | Date | Source |\n")
            f.write("|----------|----------|------|--------|\n")
            for doc in court_index:
                filename = doc.get('filename', '')
                doc_type = doc.get('doc_type', '')
                date = doc.get('date', '')
                source = doc.get('source', '')[:50]  # Truncate long URLs
                f.write(f"| {filename} | {doc_type} | {date} | {source}... |\n")
        else:
            f.write("*No court documents found*\n")
        f.write("\n")

        # FOIA media
        f.write("### FOIA Media\n\n")
        if media_index:
            f.write("| Filename | Size | Source |\n")
            f.write("|----------|------|--------|\n")
            for media in media_index:
                filename = media.get('filename', '')
                size = media.get('size_mb', '0')
                source = media.get('source_url', '')[:50]
                f.write(f"| {filename} | {size} MB | {source}... |\n")
        else:
            f.write("*No FOIA media found*\n")
        f.write("\n")

        # News articles
        f.write("### News Articles\n\n")
        if news_index:
            f.write("| Filename | Title | Date |\n")
            f.write("|----------|-------|------|\n")
            for article in news_index[:10]:  # Limit to 10 in README
                filename = article.get('filename', '')
                title = article.get('title', '')[:60]
                date = article.get('date', '')
                f.write(f"| {filename} | {title}... | {date} |\n")
            if len(news_index) > 10:
                f.write(f"\n*... and {len(news_index) - 10} more articles*\n")
        else:
            f.write("*No news articles found*\n")
        f.write("\n")

        # Summary statistics
        f.write("## Summary\n\n")
        f.write(f"- **Court documents**: {len(court_index)}\n")
        f.write(f"- **FOIA media files**: {len(media_index)}\n")
        f.write(f"- **News articles**: {len(news_index)}\n")
        f.write(f"- **Total package items**: {len(court_index) + len(media_index) + len(news_index) + 1}\n")

    print(f"  ✅ Generated: README.md")


def create_bundle_zip(working_dir):
    """Create zip archive of the entire case folder"""
    print(f"\n📦 Creating bundle archive...")

    slug = working_dir.name
    zip_filename = f"{slug}_bundle.zip"
    zip_path = working_dir / zip_filename

    # Files/directories to exclude from zip
    exclude = {zip_filename, '.git', '__pycache__', '.DS_Store'}

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in working_dir.rglob('*'):
            if file_path.is_file():
                # Skip excluded files
                if any(excl in file_path.parts for excl in exclude):
                    continue

                arcname = file_path.relative_to(working_dir.parent)
                zipf.write(file_path, arcname)

    zip_size = zip_path.stat().st_size / 1024 / 1024
    print(f"  ✅ Created: {zip_filename} ({zip_size:.1f} MB)")

    return zip_path


def main():
    working_dir = Path.cwd()
    print(f"📁 Working directory: {working_dir}")

    # Analyze cues
    cues_file = working_dir / 'cues.json'
    bucket_stats = analyze_cues(cues_file)

    # Create visualization
    chart_file = working_dir / 'composition_chart.png'
    create_visualization(bucket_stats, chart_file)

    # Generate README
    generate_readme(working_dir, bucket_stats)

    # Create zip bundle
    bundle_path = create_bundle_zip(working_dir)

    print("\n✅ Packaging complete!")
    print(f"\n📦 Bundle ready: {bundle_path}")
    print(f"   You can now distribute this case bundle.")


if __name__ == '__main__':
    main()
