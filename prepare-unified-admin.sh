#!/bin/bash

# Unified Admin Panel Creation
# Creates a single admin.html with all features merged

echo "🔧 Creating unified admin panel..."

cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/FacultyScheduling/moonlighter-web

# Pull latest
git pull origin ischedule

echo "✅ Ready to create unified admin panel"
echo ""
echo "The new admin.html will have these tabs:"
echo "  1. 👥 Manage Providers (Faculty management)"
echo "  2. 🌙 Moonlighting/IRPA (Moonlighting scheduling)"
echo "  3. 📊 Overview (System stats)"
echo "  4. ⚙️ Configure Periods (Service availability config)"
echo "  5. 📈 View Provider Requests (Request management)"
echo "  6. 📅 Manage Weeks (Week editing)"
echo ""
echo "Next: I'll create the unified admin.html file and push it"
