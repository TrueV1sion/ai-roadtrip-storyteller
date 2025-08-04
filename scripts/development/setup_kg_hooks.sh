#!/bin/bash
# Setup Knowledge Graph Git Hooks

echo "🔧 Setting up Knowledge Graph Git hooks..."

# Configure git to use our hooks directory
git config core.hooksPath .githooks

# Make all hooks executable
chmod +x .githooks/*

# Check if jq is installed (needed for JSON parsing in hooks)
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq is required for git hooks but not installed"
    echo "Install with: sudo apt-get install jq (or brew install jq on macOS)"
fi

echo "✅ Git hooks configured!"
echo ""
echo "The following hooks are now active:"
echo "- pre-commit: Validates all commits with Knowledge Graph"
echo ""
echo "To bypass hooks (not recommended): git commit --no-verify"
echo "To disable hooks: git config --unset core.hooksPath"