#!/bin/bash
pack_id=$1
if [ -z "$pack_id" ]; then
    echo "Usage: ./tools/forge_release.sh <pack_id>"
    exit 1
fi
echo "!packs/${pack_id}/" >> .gitignore
git add packs/${pack_id}/ .gitignore
git commit -m "Add ${pack_id} pack"
git push origin dev
