#!/bin/bash
# Add a milestone to the docs/index.html page
# Usage: ./tools/add_milestone.sh "Description of milestone"

if [ -z "$1" ]; then
    echo "Usage: ./tools/add_milestone.sh \"Description of milestone\""
    exit 1
fi

DATE=$(date +%Y-%m-%d)
MILESTONE="                        <li><span class=\"milestone-date\">$DATE<\/span> $1<\/li>"

# Insert after the milestones-list opening tag
sed -i '' "s|<ul class=\"milestones-list\">|<ul class=\"milestones-list\">\\
$MILESTONE|" docs/index.html

echo "✓ Added milestone: $1"
echo "  Don't forget to commit and push!"
