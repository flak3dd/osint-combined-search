#!/bin/bash
# SuperGrok OSINT Combined Search v4 - One-Command Installer
# Run: curl -fsSL https://raw.githubusercontent.com/your-org/osint-combined/main/install.sh | bash

set -e

echo -e "\033[1;36m"
cat << "EOF"
   _____ _    _ _____  ______ _____   _____ _____   ____  _  __
  / ____| |  | |  __ \|  ____|  __ \ / ____|  __ \ / __ \| |/ /
 | (___ | |  | | |__) | |__  | |__) | |  __| |__) | |  | | ' / 
  \___ \| |  | |  ___/|  __| |  _  /| | |_ |  _  /| |  | |  <  
  ____) | |__| | |    | |____| | \ \| |__| | | \ \| |__| | . \ 
 |_____/ \____/|_|    |______|_|  \_\\_____|_|  \_\\____/|_|\_\
                                                                
          SUPER GROK EDITION v4 • xAI Powered OSINT
EOF
echo -e "\033[0m"

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "Unsupported OS. Please install manually."
    exit 1
fi

echo "[+] Detected: $OS"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[-] Python 3.10+ required. Installing..."
    if [[ "$OS" == "linux" ]]; then
        sudo apt update && sudo apt install -y python3.10 python3-pip python3-venv
    else
        echo "Please install Python 3.10+ from python.org"
        exit 1
    fi
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if (( $(echo "$PYTHON_VERSION < 3.10" | bc -l) )); then
    echo "[-] Python 3.10+ required. Current: $PYTHON_VERSION"
    exit 1
fi

echo "[+] Python $PYTHON_VERSION OK"

# Create isolated env
INSTALL_DIR="$HOME/.osint-supergrok"
VENV_DIR="$INSTALL_DIR/venv"

echo "[+] Creating virtual environment at $VENV_DIR"
mkdir -p "$INSTALL_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "[+] Upgrading pip..."
pip install --upgrade pip wheel

echo "[+] Installing dependencies (including openai for Grok)..."
pip install -r <(curl -fsSL https://raw.githubusercontent.com/your-org/osint-combined/main/requirements.txt 2>/dev/null || printf "requests\npython-dotenv\nrich\nmarkdown\nflask\nflask-wtf\nopenai\ngunicorn\nPillow\ntabulate\n")

echo "[+] Downloading latest SuperGrok scripts..."
curl -fsSL https://raw.githubusercontent.com/your-org/osint-combined/main/osint_combined_search.py -o "$INSTALL_DIR/osint_combined_search.py"
curl -fsSL https://raw.githubusercontent.com/your-org/osint-combined/main/osint_web_app.py -o "$INSTALL_DIR/osint_web_app.py"
curl -fsSL https://raw.githubusercontent.com/your-org/osint-combined/main/README.md -o "$INSTALL_DIR/README.md"

chmod +x "$INSTALL_DIR/osint_combined_search.py"

# Create global commands
echo "[+] Creating launcher commands..."

cat > "$INSTALL_DIR/osint-search" << 'EOF'
#!/bin/bash
source "$HOME/.osint-supergrok/venv/bin/activate"
python "$HOME/.osint-supergrok/osint_combined_search.py" "$@"
EOF
chmod +x "$INSTALL_DIR/osint-search"

cat > "$INSTALL_DIR/osint-web" << 'EOF'
#!/bin/bash
source "$HOME/.osint-supergrok/venv/bin/activate"
python "$HOME/.osint-supergrok/osint_web_app.py"
EOF
chmod +x "$INSTALL_DIR/osint-web"

# Symlink to PATH
sudo ln -sf "$INSTALL_DIR/osint-search" /usr/local/bin/osint-search 2>/dev/null || true
sudo ln -sf "$INSTALL_DIR/osint-web" /usr/local/bin/osint-web 2>/dev/null || true

# Desktop entry (Linux)
if [[ "$OS" == "linux" ]]; then
    mkdir -p "$HOME/.local/share/applications"
    cat > "$HOME/.local/share/applications/osint-supergrok.desktop" << EOF
[Desktop Entry]
Name=SuperGrok OSINT
Comment=xAI Powered OSINT Intelligence Platform
Exec=$INSTALL_DIR/osint-web
Icon=applications-internet
Terminal=false
Type=Application
Categories=Network;Security;
EOF
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo -e "\033[1;32m"
echo "✅ Installation Complete!"
echo -e "\033[0m"
echo "Next steps:"
echo "  1. Set your API keys:"
echo "     export OSINT_INDUSTRIES_API_KEY=..."
echo "     export DEHASHED_API_KEY=..."
echo "     export CYPHER_DYNAMICS_API_KEY=..."
echo "     export GROK_API_KEY=sk-...          # ← NEW for SuperGrok AI"
echo ""
echo "  2. Launch:"
echo "     osint-search -q victim@company.com --supergrok --pretty"
echo "     osint-web"
echo ""
echo "  3. Full docs: cat $INSTALL_DIR/README.md"
echo ""
echo "Get Grok API key: https://console.x.ai/"
echo ""
echo "Happy hunting! 🕵️‍♂️"