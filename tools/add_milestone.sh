#!/bin/bash
# Add a milestone to the docs/index.html page
# Usage: ./tools/add_milestone.sh "Description of milestone"

if [ -z "$1" ]; then
    echo "Usage: ./tools/add_milestone.sh \"Description of milestone\""
    exit 1
fi

DATE=$(date +%Y-%m-%d)

# Create the new line
NEW_LINE="                <li><span class=\"milestone-date\">$DATE</span> $1</li>"

# Use awk instead of sed for better macOS compatibility
awk -v newline="$NEW_LINE" '
    /<ul class="milestones-list">/ {
        print
        print newline
        next
    }
    { print }
' docs/index.html > docs/index.html.tmp && mv docs/index.html.tmp docs/index.html

echo "✓ Added milestone: $1"
echo "  Don't forget to commit and push!"
