#!/bin/bash
# Create a zip of dev branch for Claude
cd ~/repos/noise-engine || exit 1

BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "dev" ]; then
    echo "⚠️  On $BRANCH, switching to dev..."
    git checkout dev || exit 1
fi

git archive -o ~/Downloads/noise-engine-dev.zip HEAD
echo "✅ Created ~/Downloads/noise-engine-dev.zip"
