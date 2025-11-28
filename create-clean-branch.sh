#!/bin/bash

# Clean Branch Creation Script
# This creates ischedule-clean branch with resolved filename conflicts

echo "🧹 Creating clean branch..."

# Make sure we're in the right place
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository. Run this from your moonlighter-web directory."
    exit 1
fi

# Fetch latest
echo "📥 Fetching latest changes..."
git fetch origin

# Create new branch from ischedule
echo "🌿 Creating ischedule-clean branch..."
git checkout -b ischedule-clean origin/ischedule

# Remove conflicting lowercase admin.html
echo "🗑️  Removing conflicting admin.html..."
if [ -f "admin.html" ]; then
    git rm admin.html
    git commit -m "Remove conflicting lowercase admin.html"
fi

# Rename Admin.html to admin-moonlighting.html
echo "📝 Renaming Admin.html to admin-moonlighting.html..."
if [ -f "Admin.html" ]; then
    git mv Admin.html admin-moonlighting.html
    git commit -m "Rename Admin.html to admin-moonlighting.html for clarity"
fi

# Push to origin
echo "⬆️  Pushing ischedule-clean branch..."
git push -u origin ischedule-clean

echo ""
echo "✅ Done! Clean branch created successfully."
echo ""
echo "📋 Next steps:"
echo "   1. Restart your server: python -m uvicorn backend.app:app --reload"
echo "   2. Access moonlighting admin: http://localhost:8000/admin-moonlighting.html"
echo "   3. Access service config: http://localhost:8000/admin-config.html"
echo ""
