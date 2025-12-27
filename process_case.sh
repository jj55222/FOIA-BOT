#!/usr/bin/env bash
#
# FOIA-BOT Case Processor
# Orchestrates video ingest, document scraping, and bundle creation
#
# Usage: ./process_case.sh <youtube_url> [custom_slug]
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: YouTube URL required${NC}"
    echo "Usage: $0 <youtube_url> [custom_slug]"
    echo ""
    echo "Example:"
    echo "  $0 https://www.youtube.com/watch?v=dQw4w9WgXcQ my_case"
    exit 1
fi

VID="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Generate case directory name
if [ $# -ge 2 ]; then
    # Custom slug provided
    SLUG="${2}"
else
    # Extract video ID from URL as slug
    if [[ "$VID" =~ v=([a-zA-Z0-9_-]+) ]]; then
        VIDEO_ID="${BASH_REMATCH[1]}"
        SLUG="${VIDEO_ID}"
    else
        # Fallback to timestamp
        SLUG="case_$(date +%s)"
    fi
fi

# Create case directory with date prefix
CASE_DIR="case_$(date +%Y%m%d)_${SLUG}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         FOIA-BOT Case Processing Pipeline              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Video URL:${NC} $VID"
echo -e "${GREEN}Case directory:${NC} $CASE_DIR"
echo ""

# Create and enter case directory
mkdir -p "$CASE_DIR"
cd "$CASE_DIR"

# Log file
LOG_FILE="processing.log"
echo "Processing started: $(date)" > "$LOG_FILE"

# Function to run a step
run_step() {
    local step_num=$1
    local step_name=$2
    local command=$3

    echo -e "\n${YELLOW}[$step_num/5]${NC} ${BLUE}$step_name${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if eval "$command" 2>&1 | tee -a "$LOG_FILE"; then
        echo -e "${GREEN}✓ $step_name completed${NC}"
    else
        echo -e "${RED}✗ $step_name failed${NC}"
        echo -e "${YELLOW}Check $LOG_FILE for details${NC}"
        # Continue anyway - some steps may fail if no data found
    fi
}

# Step 1: Video Ingest
run_step 1 "Video Ingest" "python3 \"$SCRIPT_DIR/video_ingest.py\" \"$VID\""

# Step 2: Court Documents
run_step 2 "Court Document Search" "python3 \"$SCRIPT_DIR/court_docs.py\""

# Step 3: FOIA Media Scraping
run_step 3 "FOIA Media Scraping" "python3 \"$SCRIPT_DIR/foia_media_scraper.py\""

# Step 4: News Scraping
run_step 4 "News Article Collection" "python3 \"$SCRIPT_DIR/news_scraper.py\""

# Step 5: Packaging
run_step 5 "Bundle Packaging" "python3 \"$SCRIPT_DIR/packager.py\""

# Final output
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Processing Complete                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Case bundle created successfully${NC}"
echo ""
echo -e "${YELLOW}Output location:${NC}"
echo -e "  📁 $CASE_DIR/"
echo -e "  📦 $CASE_DIR/${CASE_DIR}_bundle.zip"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Review the README.md in the case directory"
echo -e "  2. Check composition_chart.png for content breakdown"
echo -e "  3. Share the bundle zip file as needed"
echo ""
