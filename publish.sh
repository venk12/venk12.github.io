#!/bin/bash

# Add all changes
if git add .; then
  echo "✅ Files staged successfully."
else
  echo "❌ Failed to stage files."
  exit 1
fi

# Commit with a message passed as argument, or default to "update"
commit_message=${1:-"update"}
if git commit -m "$commit_message"; then
  echo "✅ Commit created with message: $commit_message"
else
  echo "❌ Commit failed (maybe nothing to commit?)."
  exit 1
fi

# Push to main
if git push origin main; then
  echo "🚀 Push to 'main' successful!"
else
  echo "❌ Push failed. Check your network or branch."
  exit 1
fi