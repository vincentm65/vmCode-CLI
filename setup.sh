#!/bin/bash
# bone-agent setup script for git clone installation
# This script sets up bone-agent as a system command

set -e

echo "=========================================="
echo "  bone-agent Setup"
echo "=========================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Check Python
echo "🐍 Checking for Python 3.9+..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed"
    echo "Please install Python 3.9 or later from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

echo "✓ Found Python $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo "❌ Error: Python 3.9+ is required (found $PYTHON_VERSION)"
    exit 1
fi

echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd "$PROJECT_ROOT"
pip3 install -q -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Python dependencies installed"
else
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo ""

# Setup config
if [ ! -f "config.yaml" ]; then
    if [ -f "config.yaml.example" ]; then
        echo "⚙️  Creating config.yaml from example..."
        cp config.yaml.example config.yaml
        echo "✓ config.yaml created"
        echo ""
        echo "⚠️  IMPORTANT: Edit config.yaml and add your API keys!"
        echo "   Or set them via environment variables:"
        echo "   export OPENAI_API_KEY='sk-your-key-here'"
        echo ""
    else
        echo "⚠️  Warning: config.yaml.example not found"
    fi
else
    echo "✓ config.yaml already exists"
fi

# Create bone alias/command
echo ""
echo "🔗 Setting up bone-agent command..."

# Option 1: Create symlink to user's bin directory
USER_BIN="$HOME/.local/bin"
mkdir -p "$USER_BIN"

if [ -w "$USER_BIN" ]; then
    # Create a symlink to the main.py script
    cat > "$USER_BIN/bone-agent" << 'EOF'
#!/bin/bash
# bone-agent launcher
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1"
python3 src/ui/main.py "$@"
EOF
    
    chmod +x "$USER_BIN/bone-agent"
    echo "✓ Created command: $USER_BIN/bone-agent"
    
    # Check if USER_BIN is in PATH
    if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
        echo ""
        echo "⚠️  Add $USER_BIN to your PATH:"
        echo ""
        echo "   For bash (add to ~/.bashrc):"
        echo "   export PATH=\"\$PATH:$USER_BIN\""
        echo ""
        echo "   For zsh (add to ~/.zshrc):"
        echo "   export PATH=\"\$PATH:$USER_BIN\""
        echo ""
        echo "   Then reload your shell:"
        echo "   source ~/.bashrc  # or source ~/.zshrc"
        echo ""
        echo "   Or just run:"
        echo "   export PATH=\"\$PATH:$USER_BIN\""
        echo ""
    else
        echo "✓ $USER_BIN is already in PATH"
    fi
else
    # Option 2: Create alias in shell config
    echo "⚠️  Cannot write to $USER_BIN"
    echo ""
    echo "Add this alias to your shell config (~/.bashrc or ~/.zshrc):"
    echo ""
    echo "   alias bone-agent='cd $PROJECT_ROOT && python3 src/ui/main.py'"
    echo ""
    echo "Then reload your shell: source ~/.bashrc"
fi

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Run bone-agent:"
echo "  bone-agent"
echo ""
echo "Or run directly:"
echo "  cd $PROJECT_ROOT"
echo "  python3 src/ui/main.py"
echo ""
