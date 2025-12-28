#!/usr/bin/env python3
"""
Simple VTT File Debugger
Run this to see why VTT parsing is failing
"""

from pathlib import Path
import sys

def debug_vtt(vtt_file):
    """Show VTT file structure for debugging"""

    if not vtt_file.exists():
        print(f"❌ File not found: {vtt_file}")
        return

    with open(vtt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    print("="*60)
    print(f"📄 VTT File: {vtt_file.name}")
    print("="*60)
    print(f"Total size: {len(content)} characters")
    print(f"Total lines: {len(lines)}")
    print()

    # Show first 50 lines with line numbers
    print("📝 First 50 lines:")
    print("-"*60)
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:3}: {repr(line)}")  # Use repr to see special chars

    print()
    print("="*60)

    # Try to identify format
    print("🔍 Format Detection:")

    # Check for WEBVTT header
    if lines[0].strip().upper().startswith('WEBVTT'):
        print("✓ Has WEBVTT header")
    else:
        print("✗ No WEBVTT header found")

    # Check for timestamp patterns
    import re

    timestamp_patterns = {
        'Full (HH:MM:SS.mmm)': r'\d{2}:\d{2}:\d{2}\.\d{3}',
        'Short (MM:SS.mmm)': r'\d{2}:\d{2}\.\d{3}',
        'No milliseconds (HH:MM:SS)': r'\d{2}:\d{2}:\d{2}',
    }

    for name, pattern in timestamp_patterns.items():
        matches = re.findall(pattern, content)
        if matches:
            print(f"✓ Found {len(matches)} {name} timestamps")
            print(f"  Example: {matches[0]}")

    # Check for arrow separator
    if '-->' in content:
        arrow_count = content.count('-->')
        print(f"✓ Found {arrow_count} '-->' separators")
    else:
        print("✗ No '-->' separator found")

    # Show some timestamp lines
    print()
    print("🕐 Sample timestamp lines:")
    for i, line in enumerate(lines):
        if '-->' in line:
            # Show context: previous line, this line, next line
            print(f"  Line {i}:   {repr(lines[i-1]) if i > 0 else ''}")
            print(f"  Line {i+1}: {repr(line)}")
            print(f"  Line {i+2}: {repr(lines[i+1]) if i+1 < len(lines) else ''}")
            print()
            if i > 100:  # Only show first few examples
                break

    print("="*60)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_vtt.py <path_to_vtt_file>")
        sys.exit(1)

    vtt_path = Path(sys.argv[1])
    debug_vtt(vtt_path)
