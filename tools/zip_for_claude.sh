#!/bin/bash
# Create a zip of current branch for Claude
cd ~/repos/noise-engine || exit 1
BRANCH=$(git branch --show-current)
git archive -o ~/Downloads/noise-engine-$BRANCH.zip HEAD
echo "✅ Created ~/Downloads/noise-engine-$BRANCH.zip from $BRANCH"
