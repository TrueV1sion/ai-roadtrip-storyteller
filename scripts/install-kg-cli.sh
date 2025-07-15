#!/bin/bash
# Install Knowledge Graph CLI tool

echo "📦 Installing Knowledge Graph CLI..."

# Check Python version
if ! python3 --version | grep -E "3\.(9|10|11|12)" > /dev/null; then
    echo "❌ Python 3.9+ required"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install --user click httpx rich websocket-client

# Create symlink for global access
if [ -w "/usr/local/bin" ]; then
    ln -sf "$(pwd)/scripts/kg-cli.py" /usr/local/bin/roadtrip-kg
    echo "✅ Installed as 'roadtrip-kg' command"
else
    # Alternative: add to PATH
    echo "#!/bin/bash" > ~/bin/roadtrip-kg
    echo "python3 $(pwd)/scripts/kg-cli.py \"\$@\"" >> ~/bin/roadtrip-kg
    chmod +x ~/bin/roadtrip-kg
    
    if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
        echo "export PATH=\"\$HOME/bin:\$PATH\"" >> ~/.bashrc
        echo "⚠️  Added ~/bin to PATH. Run: source ~/.bashrc"
    fi
    echo "✅ Installed as 'roadtrip-kg' command in ~/bin"
fi

echo ""
echo "🎉 Knowledge Graph CLI installed!"
echo ""
echo "Usage examples:"
echo "  roadtrip-kg status              # Check KG and agent status"
echo "  roadtrip-kg impact <file>       # Analyze file impact"
echo "  roadtrip-kg search <query>      # Search for patterns"
echo "  roadtrip-kg analyze <file>      # Full agent analysis"
echo "  roadtrip-kg validate <files...> # Validate before commit"
echo "  roadtrip-kg watch              # Watch real-time events"
echo ""
echo "Run 'roadtrip-kg --help' for all commands"