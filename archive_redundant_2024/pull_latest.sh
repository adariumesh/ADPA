#!/bin/bash

# Script to pull latest changes and integrate with our work
echo "🔄 Pulling latest ADPA changes..."

# Save our current work
echo "📦 Stashing current changes..."
git add .
git stash push -m "Pre-pull integration work $(date)"

# Fetch latest changes
echo "📡 Fetching latest from origin..."
git fetch origin

# Pull main branch
echo "⬇️ Pulling main branch..."
git pull origin main

# Apply our stashed work back
echo "🔄 Restoring integration work..."
git stash pop

echo "✅ Latest code pulled and integration work restored!"
echo
echo "📋 Recent commits:"
git log --oneline -5

echo
echo "📁 Updated files:"
git status --porcelain